# Copyright 2017 Catalyst IT Limited
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from oslo_config import cfg
from oslo_log import log as logging
import requests
import tenacity

from qinling.db import api as db_api
from qinling.engine import utils
from qinling import exceptions as exc
from qinling import status
from qinling.utils import constants
from qinling.utils import etcd_util

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class DefaultEngine(object):
    def __init__(self, orchestrator, qinling_endpoint):
        self.orchestrator = orchestrator
        self.qinling_endpoint = qinling_endpoint
        self.session = requests.Session()

    def create_runtime(self, ctx, runtime_id):
        LOG.info('Start to create runtime %s.', runtime_id)

        with db_api.transaction():
            runtime = db_api.get_runtime(runtime_id)

            try:
                self.orchestrator.create_pool(
                    runtime_id,
                    runtime.image,
                    trusted=runtime.trusted
                )
                runtime.status = status.AVAILABLE
                LOG.info('Runtime %s created.', runtime_id)
            except Exception as e:
                LOG.exception(
                    'Failed to create pool for runtime %s. Error: %s',
                    runtime_id,
                    str(e)
                )
                runtime.status = status.ERROR

    def delete_runtime(self, ctx, runtime_id):
        LOG.info('Start to delete runtime %s.', runtime_id)

        self.orchestrator.delete_pool(runtime_id)
        db_api.delete_runtime(runtime_id)

        LOG.info('Deleted runtime %s.', runtime_id)

    def update_runtime(self, ctx, runtime_id, image=None, pre_image=None):
        LOG.info(
            'Start to update runtime %s, image: %s, pre_image: %s',
            runtime_id, image, pre_image
        )

        ret = self.orchestrator.update_pool(runtime_id, image=image)

        if ret:
            values = {'status': status.AVAILABLE}
            db_api.update_runtime(runtime_id, values)

            LOG.info('Updated runtime %s.', runtime_id)
        else:
            values = {'status': status.AVAILABLE, 'image': pre_image}
            db_api.update_runtime(runtime_id, values)

            LOG.info('Rollbacked runtime %s.', runtime_id)

    def get_runtime_pool(self, ctx, runtime_id):
        LOG.info("Getting pool information for runtime %s", runtime_id)

        return self.orchestrator.get_pool(runtime_id)

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        stop=tenacity.stop_after_attempt(30),
        reraise=True,
        retry=tenacity.retry_if_exception_type(exc.EtcdLockException)
    )
    def function_load_check(self, function_id, version, runtime_id):
        """Check function load and scale the workers if needed.

        :return: None if no need to scale up otherwise return the service url
        """
        with etcd_util.get_worker_lock(function_id, version) as lock:
            if not lock.is_acquired():
                raise exc.EtcdLockException(
                    'Etcd: failed to get worker lock for function %s'
                    '(version %s).' % (function_id, version)
                )

            workers = etcd_util.get_workers(function_id, version)
            running_execs = db_api.get_executions(
                function_id=function_id,
                function_version=version,
                status=status.RUNNING
            )
            concurrency = (len(running_execs) or 1) / (len(workers) or 1)
            if (len(workers) == 0 or
                    concurrency > CONF.engine.function_concurrency):
                LOG.info(
                    'Scale up function %s(version %s). Current concurrency: '
                    '%s, execution number %s, worker number %s',
                    function_id, version, concurrency, len(running_execs),
                    len(workers)
                )

                # NOTE(kong): The increase step could be configurable
                return self.scaleup_function(None, function_id, version,
                                             runtime_id, 1)

    def create_execution(self, ctx, execution_id, function_id,
                         function_version, runtime_id, input=None):
        LOG.info(
            'Creating execution. execution_id=%s, function_id=%s, '
            'function_version=%s, runtime_id=%s, input=%s',
            execution_id, function_id, function_version, runtime_id, input
        )

        function = db_api.get_function(function_id)
        source = function.code['source']
        rlimit = {
            'cpu': function.cpu,
            'memory_size': function.memory_size
        }
        image = None
        identifier = None
        labels = None
        svc_url = None
        is_image_source = source == constants.IMAGE_FUNCTION

        # Auto scale workers if needed
        if not is_image_source:
            try:
                svc_url = self.function_load_check(function_id,
                                                   function_version,
                                                   runtime_id)
            except (
                exc.OrchestratorException,
                exc.EtcdLockException
            ) as e:
                utils.handle_execution_exception(execution_id, str(e))
                return

        temp_url = etcd_util.get_service_url(function_id, function_version)
        svc_url = svc_url or temp_url
        if svc_url:
            func_url = '%s/execute' % svc_url
            LOG.debug(
                'Found service url for function: %s(version %s), execution: '
                '%s, url: %s',
                function_id, function_version, execution_id, func_url
            )

            data = utils.get_request_data(
                CONF, function_id, function_version, execution_id,
                rlimit, input, function.entry, function.trust_id,
                self.qinling_endpoint, function.timeout
            )
            success, res = utils.url_request(
                self.session, func_url, body=data
            )

            utils.finish_execution(execution_id, success, res,
                                   is_image_source=is_image_source)
            return

        if is_image_source:
            image = function.code['image']
            identifier = ('%s-%s' % (execution_id, function_id))[:63]
        else:
            identifier = runtime_id
            labels = {'runtime_id': runtime_id}

        try:
            # For image function, it will be executed inside this method;
            # For package type function it only sets up underlying resources
            # and get a service url. If the service url is already created
            # beforehand, nothing happens.
            _, svc_url = self.orchestrator.prepare_execution(
                function_id,
                function_version,
                rlimit=rlimit,
                image=image,
                identifier=identifier,
                labels=labels,
                input=input,
            )
        except exc.OrchestratorException as e:
            utils.handle_execution_exception(execution_id, str(e))
            return

        # For image type function, wait for its completion and retrieve the
        # worker log;
        # For package type function, invoke and get log
        success, res = self.orchestrator.run_execution(
            execution_id,
            function_id,
            function_version,
            rlimit=rlimit if svc_url else None,
            input=input,
            identifier=identifier,
            service_url=svc_url,
            entry=function.entry,
            trust_id=function.trust_id,
            timeout=function.timeout
        )

        utils.finish_execution(execution_id, success, res,
                               is_image_source=is_image_source)

    def delete_function(self, ctx, function_id, function_version=0):
        """Deletes underlying resources allocated for function."""
        LOG.info('Start to delete function %s(version %s).', function_id,
                 function_version)

        self.orchestrator.delete_function(function_id, function_version)

        LOG.info('Deleted function %s(version %s).', function_id,
                 function_version)

    def scaleup_function(self, ctx, function_id, function_version, runtime_id,
                         count=1):
        worker_names, service_url = self.orchestrator.scaleup_function(
            function_id,
            function_version,
            identifier=runtime_id,
            count=count
        )

        for name in worker_names:
            etcd_util.create_worker(function_id, name,
                                    version=function_version)

        etcd_util.create_service_url(function_id, service_url,
                                     version=function_version)

        LOG.info('Finished scaling up function %s(version %s).', function_id,
                 function_version)

        return service_url

    def scaledown_function(self, ctx, function_id, function_version=0,
                           count=1):
        workers = etcd_util.get_workers(function_id, function_version)
        worker_deleted_num = (
            count if len(workers) > count else len(workers) - 1
        )
        workers = workers[:worker_deleted_num]

        for worker in workers:
            LOG.debug('Removing worker %s', worker)
            self.orchestrator.delete_worker(worker)
            etcd_util.delete_worker(function_id, worker,
                                    version=function_version)

        LOG.info('Finished scaling down function %s(version %s).', function_id,
                 function_version)
