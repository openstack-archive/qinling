# Copyright 2018 Catalyst IT Limited
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import collections

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import strutils
import pecan
from pecan import rest
import tenacity
from webob.static import FileIter
import wsmeext.pecan as wsme_pecan

from qinling.api import access_control as acl
from qinling.api.controllers.v1 import resources
from qinling.api.controllers.v1 import types
from qinling import context
from qinling.db import api as db_api
from qinling import exceptions as exc
from qinling import rpc
from qinling.storage import base as storage_base
from qinling.utils import constants
from qinling.utils import etcd_util
from qinling.utils import rest_utils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class FunctionVersionsController(rest.RestController):
    _custom_actions = {
        'scale_up': ['POST'],
        'scale_down': ['POST'],
        'detach': ['POST'],
    }

    def __init__(self, *args, **kwargs):
        self.type = 'function_version'
        self.storage_provider = storage_base.load_storage_provider(CONF)
        self.engine_client = rpc.get_engine_client()

        super(FunctionVersionsController, self).__init__(*args, **kwargs)

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        stop=tenacity.stop_after_attempt(30),
        reraise=True,
        retry=tenacity.retry_if_exception_type(exc.EtcdLockException)
    )
    def _create_function_version(self, project_id, function_id, **kwargs):
        with etcd_util.get_function_version_lock(function_id) as lock:
            if not lock.is_acquired():
                raise exc.EtcdLockException(
                    "Etcd: failed to acquire version lock for function %s." %
                    function_id
                )

            with db_api.transaction():
                # Get latest function package md5 and version number
                func_db = db_api.get_function(function_id, insecure=False)
                if func_db.code['source'] != constants.PACKAGE_FUNCTION:
                    raise exc.NotAllowedException(
                        "Function versioning only allowed for %s type "
                        "function." %
                        constants.PACKAGE_FUNCTION
                    )

                l_md5 = func_db.code['md5sum']
                l_version = func_db.latest_version

                if len(func_db.versions) >= constants.MAX_VERSION_NUMBER:
                    raise exc.NotAllowedException(
                        'Can not exceed maximum number(%s) of versions' %
                        constants.MAX_VERSION_NUMBER
                    )

                # Check if the latest package changed since last version
                changed = self.storage_provider.changed_since(project_id,
                                                              function_id,
                                                              l_md5,
                                                              l_version)
                if not changed:
                    raise exc.NotAllowedException(
                        'Function package not changed since the latest '
                        'version %s.' % l_version
                    )

                LOG.info("Creating %s, function_id: %s, old_version: %d",
                         self.type, function_id, l_version)

                # Create new version and copy package.
                self.storage_provider.copy(project_id, function_id, l_md5,
                                           l_version)
                version = db_api.increase_function_version(function_id,
                                                           l_version,
                                                           **kwargs)
                func_db.latest_version = l_version + 1

            LOG.info("New version %d for function %s created.", l_version + 1,
                     function_id)
            return version

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(
        resources.FunctionVersion,
        types.uuid,
        body=resources.FunctionVersion,
        status_code=201
    )
    def post(self, function_id, body):
        """Create a new version for the function.

        Only allow to create version for package type function.

        The supported boy params:
            - description: Optional. The description of the new version.
        """
        ctx = context.get_ctx()
        acl.enforce('function_version:create', ctx)

        params = body.to_dict()
        values = {
            'description': params.get('description'),
        }

        # Try to create a new function version within lock and db transaction
        try:
            version = self._create_function_version(
                ctx.project_id, function_id, **values
            )
        except exc.EtcdLockException as e:
            LOG.exception(str(e))
            # Reraise a generic exception as the end users should not know
            # the underlying details.
            raise exc.QinlingException('Internal server error.')

        return resources.FunctionVersion.from_db_obj(version)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.FunctionVersions, types.uuid)
    def get_all(self, function_id):
        """Get all the versions of the given function.

        Admin user can get all versions for the normal user's function.
        """
        acl.enforce('function_version:get_all', context.get_ctx())
        LOG.info("Getting versions for function %s.", function_id)

        # Getting function and versions needs to happen in a db transaction
        with db_api.transaction():
            func_db = db_api.get_function(function_id)
            db_versions = func_db.versions

        versions = [resources.FunctionVersion.from_db_obj(v)
                    for v in db_versions]

        return resources.FunctionVersions(function_versions=versions)

    @rest_utils.wrap_pecan_controller_exception
    @pecan.expose()
    @pecan.expose('json')
    def get(self, function_id, version):
        """Get function version or download function version package.

        This method can support HTTP request using either
        'Accept:application/json' or no 'Accept' header.
        """
        ctx = context.get_ctx()
        acl.enforce('function_version:get', ctx)

        download = strutils.bool_from_string(
            pecan.request.GET.get('download', False)
        )
        version = int(version)

        version_db = db_api.get_function_version(function_id, version)

        if not download:
            LOG.info("Getting version %s for function %s.", version,
                     function_id)
            pecan.override_template('json')
            return resources.FunctionVersion.from_db_obj(version_db).to_dict()

        LOG.info("Downloading version %s for function %s.", version,
                 function_id)

        f = self.storage_provider.retrieve(version_db.project_id, function_id,
                                           None, version=version)

        if isinstance(f, collections.Iterable):
            pecan.response.app_iter = f
        else:
            pecan.response.app_iter = FileIter(f)
        pecan.response.headers['Content-Type'] = 'application/zip'
        pecan.response.headers['Content-Disposition'] = (
            'attachment; filename="%s_%s"' % (function_id, version)
        )

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(None, types.uuid, int, status_code=204)
    def delete(self, function_id, version):
        """Delete a specific function version.

        - The version should not being used by any job
        - The version should not being used by any webhook
        - Admin user can not delete normal user's version
        """
        ctx = context.get_ctx()
        acl.enforce('function_version:delete', ctx)
        LOG.info("Deleting version %s of function %s.", version, function_id)

        with db_api.transaction():
            version_db = db_api.get_function_version(function_id, version,
                                                     insecure=False)
            latest_version = version_db.function.latest_version

            version_jobs = db_api.get_jobs(
                function_id=version_db.function_id,
                function_version=version_db.version_number,
                status={'nin': ['done', 'cancelled']}
            )
            if len(version_jobs) > 0:
                raise exc.NotAllowedException(
                    'The function version is still associated with running '
                    'job(s).'
                )

            version_webhook = db_api.get_webhooks(
                function_id=version_db.function_id,
                function_version=version_db.version_number,
            )
            if len(version_webhook) > 0:
                raise exc.NotAllowedException(
                    'The function version is still associated with webhook.'
                )

            filters = rest_utils.get_filters(
                function_id=version_db.function_id,
                function_version=version_db.version_number
            )
            version_aliases = db_api.get_function_aliases(**filters)
            if len(version_aliases) > 0:
                raise exc.NotAllowedException(
                    'The function version is still associated with alias.'
                )

            # Delete resources for function version
            self.engine_client.delete_function(function_id, version=version)
            etcd_util.delete_function(function_id, version=version)

            self.storage_provider.delete(ctx.projectid, function_id, None,
                                         version=version)

            db_api.delete_function_version(function_id, version)

            if latest_version == version:
                version_db.function.latest_version = latest_version - 1

        LOG.info("Version %s of function %s deleted.", version, function_id)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(
        None,
        types.uuid,
        int,
        body=resources.ScaleInfo,
        status_code=202
    )
    def scale_up(self, function_id, version, scale):
        """Scale up the workers for function version execution.

        This is admin only operation. The load monitoring of execution
        depends on the monitoring solution of underlying orchestrator.
        """
        acl.enforce('function_version:scale_up', context.get_ctx())

        func_db = db_api.get_function(function_id)

        # If version=0, it's equivalent to /functions/<funcion-id>/scale_up
        if version > 0:
            db_api.get_function_version(function_id, version)

        params = scale.to_dict()

        LOG.info('Starting to scale up function %s(version %s), params: %s',
                 function_id, version, params)

        self.engine_client.scaleup_function(
            function_id,
            runtime_id=func_db.runtime_id,
            version=version,
            count=params['count']
        )

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(
        None,
        types.uuid,
        int,
        body=resources.ScaleInfo,
        status_code=202
    )
    def scale_down(self, function_id, version, scale):
        """Scale down the workers for function version execution.

        This is admin only operation. The load monitoring of execution
        depends on the monitoring solution of underlying orchestrator.
        """
        acl.enforce('function_version:scale_down', context.get_ctx())

        db_api.get_function(function_id)
        params = scale.to_dict()

        # If version=0, it's equivalent to /functions/<funcion-id>/scale_down
        if version > 0:
            db_api.get_function_version(function_id, version)

        workers = etcd_util.get_workers(function_id, version=version)
        if len(workers) <= 1:
            LOG.info('No need to scale down function %s(version %s)',
                     function_id, version)
            return

        LOG.info('Starting to scale down function %s(version %s), params: %s',
                 function_id, version, params)
        self.engine_client.scaledown_function(function_id, version=version,
                                              count=params['count'])

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(None, types.uuid, int, status_code=202)
    def detach(self, function_id, version):
        """Detach the function version from its underlying workers.

        This is admin only operation, which gives admin user a safe way to
        clean up the underlying resources allocated for the function version.
        """
        acl.enforce('function_version:detach', context.get_ctx())

        db_api.get_function(function_id)
        # If version=0, it's equivalent to /functions/<funcion-id>/detach
        if version > 0:
            db_api.get_function_version(function_id, version)

        LOG.info('Starting to detach function %s(version %s)', function_id,
                 version)

        # Delete allocated resources in orchestrator and etcd keys.
        self.engine_client.delete_function(function_id, version=version)
        etcd_util.delete_function(function_id, version=version)
