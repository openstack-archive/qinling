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

from qinling.db import api as db_api
from qinling import status
from qinling.utils import common

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class DefaultEngine(object):
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def create_runtime(self, ctx, runtime_id):
        LOG.info('Start to create.',
                 resource={'type': 'runtime', 'id': runtime_id})

        with db_api.transaction():
            runtime = db_api.get_runtime(runtime_id)
            labels = {'runtime_id': runtime_id}

            try:
                self.orchestrator.create_pool(
                    runtime_id,
                    runtime.image,
                    labels=labels,
                )
                runtime.status = status.AVAILABLE
            except Exception as e:
                LOG.exception(
                    'Failed to create pool for runtime %s. Error: %s',
                    runtime_id,
                    str(e)
                )
                runtime.status = status.ERROR

    def delete_runtime(self, ctx, runtime_id):
        resource = {'type': 'runtime', 'id': runtime_id}
        LOG.info('Start to delete.', resource=resource)

        labels = {'runtime_id': runtime_id}
        self.orchestrator.delete_pool(runtime_id, labels=labels)
        db_api.delete_runtime(runtime_id)

        LOG.info('Deleted.', resource=resource)

    def update_runtime(self, ctx, runtime_id, image=None, pre_image=None):
        resource = {'type': 'runtime', 'id': runtime_id}
        LOG.info('Start to update, image=%s', image, resource=resource)

        labels = {'runtime_id': runtime_id}
        ret = self.orchestrator.update_pool(
            runtime_id, labels=labels, image=image
        )

        if ret:
            values = {'status': status.AVAILABLE}
            db_api.update_runtime(runtime_id, values)

            LOG.info('Updated.', resource=resource)
        else:
            values = {'status': status.AVAILABLE, 'image': pre_image}
            db_api.update_runtime(runtime_id, values)

            LOG.info('Rollbacked.', resource=resource)

    def create_execution(self, ctx, execution_id, function_id, runtime_id,
                         input=None):
        LOG.info(
            'Creating execution. execution_id=%s, function_id=%s, '
            'runtime_id=%s, input=%s',
            execution_id, function_id, runtime_id, input
        )

        with db_api.transaction():
            execution = db_api.get_execution(execution_id)
            function = db_api.get_function(function_id)

            if function.service:
                func_url = '%s/execute' % function.service.service_url
                LOG.debug(
                    'Found service url for function: %s, url: %s',
                    function_id, func_url
                )

                data = {'input': input, 'execution_id': execution_id}
                r = requests.post(func_url, json=data)

                # logs = self.orchestrator.get_execution_log(
                #     execution_id,
                #     worker_name=function.service.worker_name,
                # )

                LOG.debug('Finished execution %s', execution_id)

                execution.status = status.SUCCESS
                execution.output = r.json()
                # execution.logs = logs
                return

            source = function.code['source']
            image = None
            identifier = None
            labels = None

            if source == 'image':
                image = function.code['image']
                identifier = ('%s-%s' %
                              (common.generate_unicode_uuid(dashed=False),
                               function_id)
                              )[:63]
                labels = {'function_id': function_id}
            else:
                identifier = runtime_id
                labels = {'runtime_id': runtime_id}

            worker_name, service_url = self.orchestrator.prepare_execution(
                function_id,
                image=image,
                identifier=identifier,
                labels=labels,
                input=input,
                entry=function.entry
            )
            output = self.orchestrator.run_execution(
                execution_id,
                function_id,
                input=input,
                identifier=identifier,
                service_url=service_url,
            )

            logs = ''
            # Execution log is only available for non-image source execution.
            if service_url:
                logs = self.orchestrator.get_execution_log(
                    execution_id,
                    worker_name=worker_name,
                )

            LOG.debug(
                'Finished execution. execution_id=%s, output=%s',
                execution_id,
                output
            )
            execution.output = output
            execution.logs = logs
            execution.status = status.SUCCESS

            # No service is created in orchestrator for single container.
            if not image:
                mapping = {
                    'function_id': function_id,
                    'service_url': service_url,
                }
                db_api.create_function_service_mapping(mapping)
                worker = {
                    'function_id': function_id,
                    'worker_name': worker_name
                }
                db_api.create_function_worker(worker)

    def delete_function(self, ctx, function_id):
        resource = {'type': 'function', 'id': function_id}
        LOG.info('Start to delete.', resource=resource)

        labels = {'function_id': function_id}
        self.orchestrator.delete_function(function_id, labels=labels)

        LOG.info('Deleted.', resource=resource)

    def scaleup_function(self, ctx, function_id, runtime_id):
        function = db_api.get_function(function_id)

        worker_names = self.orchestrator.scaleup_function(
            function_id,
            identifier=runtime_id,
            entry=function.entry
        )

        with db_api.transaction():
            for name in worker_names:
                worker = {
                    'function_id': function_id,
                    'worker_name': name
                }
                db_api.create_function_worker(worker)

        LOG.info('Finished scaling up function %s.', function_id)
