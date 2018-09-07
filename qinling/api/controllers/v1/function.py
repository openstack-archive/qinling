# Copyright 2017 Catalyst IT Limited
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
import json

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import strutils
import pecan
from pecan import rest
from webob.static import FileIter
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from qinling.api import access_control as acl
from qinling.api.controllers.v1 import function_version
from qinling.api.controllers.v1 import resources
from qinling.api.controllers.v1 import types
from qinling import context
from qinling.db import api as db_api
from qinling import exceptions as exc
from qinling import rpc
from qinling.storage import base as storage_base
from qinling.utils import common
from qinling.utils import constants
from qinling.utils import etcd_util
from qinling.utils.openstack import keystone as keystone_util
from qinling.utils.openstack import swift as swift_util
from qinling.utils import rest_utils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

POST_REQUIRED = set(['code'])
CODE_SOURCE = set(['package', 'swift', 'image'])
UPDATE_ALLOWED = set(['name', 'description', 'code', 'package', 'entry',
                      'cpu', 'memory_size', 'timeout'])


class FunctionWorkerController(rest.RestController):
    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.FunctionWorkers, types.uuid, int)
    def get_all(self, function_id, function_version=0):
        acl.enforce('function_worker:get_all', context.get_ctx())

        LOG.info("Getting workers for function %s(version %s).", function_id,
                 function_version)

        workers = etcd_util.get_workers(function_id, version=function_version)
        workers = [
            resources.FunctionWorker.from_dict(
                {
                    'function_id': function_id,
                    'function_version': function_version,
                    'worker_name': w
                }
            ) for w in workers
        ]

        return resources.FunctionWorkers(workers=workers)


class FunctionsController(rest.RestController):
    workers = FunctionWorkerController()
    versions = function_version.FunctionVersionsController()

    _custom_actions = {
        'scale_up': ['POST'],
        'scale_down': ['POST'],
        'detach': ['POST'],
    }

    def __init__(self, *args, **kwargs):
        self.storage_provider = storage_base.load_storage_provider(CONF)
        self.engine_client = rpc.get_engine_client()

        super(FunctionsController, self).__init__(*args, **kwargs)

    def _check_swift(self, container, object):
        # Auth needs to be enabled because qinling needs to check swift
        # object using user's credential.
        if not CONF.pecan.auth_enable:
            raise exc.InputException('Swift object not supported.')

        if not swift_util.check_object(container, object):
            raise exc.InputException('Failed to validate object in Swift.')

    @rest_utils.wrap_pecan_controller_exception
    @pecan.expose(content_type='application/zip')
    @pecan.expose('json')
    def get(self, id):
        """Get function information or download function package.

        This method can support HTTP request using either
        'Accept:application/json' or no 'Accept' header.
        """
        ctx = context.get_ctx()
        acl.enforce('function:get', ctx)

        download = strutils.bool_from_string(
            pecan.request.GET.get('download', False)
        )
        func_db = db_api.get_function(id)

        if not download:
            LOG.info("Getting function %s.", id)
            pecan.override_template('json')
            return resources.Function.from_db_obj(func_db).to_dict()

        LOG.info("Downloading function %s", id)
        source = func_db.code['source']

        if source == constants.PACKAGE_FUNCTION:
            f = self.storage_provider.retrieve(func_db.project_id, id,
                                               func_db.code['md5sum'])
        elif source == constants.SWIFT_FUNCTION:
            container = func_db.code['swift']['container']
            obj = func_db.code['swift']['object']
            f = swift_util.download_object(container, obj)
        else:
            msg = 'Download image function is not allowed.'
            pecan.abort(
                status_code=405,
                detail=msg,
                headers={'Server-Error-Message': msg}
            )

        pecan.response.app_iter = (f if isinstance(f, collections.Iterable)
                                   else FileIter(f))
        pecan.response.headers['Content-Disposition'] = (
            'attachment; filename="%s"' % id
        )

    @rest_utils.wrap_pecan_controller_exception
    @pecan.expose('json')
    def post(self, **kwargs):
        # When using image to create function, runtime_id is not a required
        # param.
        if not POST_REQUIRED.issubset(set(kwargs.keys())):
            raise exc.InputException(
                'Required param is missing. Required: %s' % POST_REQUIRED
            )
        LOG.info("Creating function, params: %s", kwargs)

        values = {
            'name': kwargs.get('name'),
            'description': kwargs.get('description'),
            'runtime_id': kwargs.get('runtime_id'),
            'code': json.loads(kwargs['code']),
            'entry': kwargs.get('entry', 'main.main'),
            'cpu': kwargs.get('cpu', CONF.resource_limits.default_cpu),
            'memory_size': kwargs.get(
                'memory_size', CONF.resource_limits.default_memory
            ),
            'timeout': kwargs.get(
                'timeout', CONF.resource_limits.default_timeout
            ),
        }

        common.validate_int_in_range(
            'timeout', values['timeout'], CONF.resource_limits.min_timeout,
            CONF.resource_limits.max_timeout
        )
        common.validate_int_in_range(
            'cpu', values['cpu'], CONF.resource_limits.min_cpu,
            CONF.resource_limits.max_cpu
        )
        common.validate_int_in_range(
            'memory', values['memory_size'], CONF.resource_limits.min_memory,
            CONF.resource_limits.max_memory
        )

        source = values['code'].get('source')
        if not source or source not in CODE_SOURCE:
            raise exc.InputException(
                'Invalid code source specified, available sources: %s' %
                ', '.join(CODE_SOURCE)
            )

        if source != constants.IMAGE_FUNCTION:
            if not kwargs.get('runtime_id'):
                raise exc.InputException('"runtime_id" must be specified.')

            runtime = db_api.get_runtime(kwargs['runtime_id'])
            if runtime.status != 'available':
                raise exc.InputException(
                    'Runtime %s is not available.' % kwargs['runtime_id']
                )

        store = False
        create_trust = True
        if source == constants.PACKAGE_FUNCTION:
            store = True
            md5sum = values['code'].get('md5sum')
            data = kwargs['package'].file.read()
        elif source == constants.SWIFT_FUNCTION:
            swift_info = values['code'].get('swift', {})

            if not (swift_info.get('container') and swift_info.get('object')):
                raise exc.InputException("Both container and object must be "
                                         "provided for swift type function.")

            self._check_swift(
                swift_info.get('container'),
                swift_info.get('object')
            )
        else:
            create_trust = False
            values['entry'] = None

        if cfg.CONF.pecan.auth_enable and create_trust:
            try:
                values['trust_id'] = keystone_util.create_trust().id
                LOG.debug('Trust %s created', values['trust_id'])
            except Exception:
                raise exc.TrustFailedException(
                    'Trust creation failed for function.'
                )

        # Create function and store the package data inside a db transaction so
        # that the function won't be created if any error happened during
        # package store.
        with db_api.transaction():
            func_db = db_api.create_function(values)
            if store:
                try:
                    ctx = context.get_ctx()
                    _, actual_md5 = self.storage_provider.store(
                        ctx.projectid, func_db.id, data, md5sum=md5sum
                    )
                    values['code'].update({"md5sum": actual_md5})
                    func_db = db_api.update_function(func_db.id, values)
                except Exception as e:
                    LOG.exception("Failed to store function package.")
                    keystone_util.delete_trust(values['trust_id'])
                    raise e

        pecan.response.status = 201
        return resources.Function.from_db_obj(func_db).to_dict()

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Functions, bool, wtypes.text)
    def get_all(self, all_projects=False, project_id=None):
        """Return a list of functions.

        :param project_id: Optional. Admin user can query other projects
            resources, the param is ignored for normal user.
        :param all_projects: Optional. Get resources of all projects.
        """
        project_id, all_projects = rest_utils.get_project_params(
            project_id, all_projects
        )
        if all_projects:
            acl.enforce('function:get_all:all_projects', context.get_ctx())

        filters = rest_utils.get_filters(
            project_id=project_id,
        )
        LOG.info("Get all functions. filters=%s", filters)
        db_functions = db_api.get_functions(insecure=all_projects, **filters)
        functions = [resources.Function.from_db_obj(db_model)
                     for db_model in db_functions]

        return resources.Functions(functions=functions)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(None, types.uuid, status_code=204)
    def delete(self, id):
        """Delete the specified function.

        Delete function will also delete all its versions.
        """
        LOG.info("Delete function %s.", id)

        with db_api.transaction():
            func_db = db_api.get_function(id)
            if len(func_db.jobs) > 0:
                raise exc.NotAllowedException(
                    'The function is still associated with running job(s).'
                )
            if len(func_db.webhooks) > 0:
                raise exc.NotAllowedException(
                    'The function is still associated with webhook(s).'
                )
            if len(func_db.aliases) > 0:
                raise exc.NotAllowedException(
                    'The function is still associated with function alias(es).'
                )

            # Even admin user can not delete other project's function because
            # the trust associated can only be removed by function owner.
            if func_db.project_id != context.get_ctx().projectid:
                raise exc.NotAllowedException(
                    'Function can only be deleted by its owner.'
                )

            # Delete trust if needed
            if func_db.trust_id:
                keystone_util.delete_trust(func_db.trust_id)

            for version_db in func_db.versions:
                # Delete all resources created by orchestrator asynchronously.
                self.engine_client.delete_function(
                    id,
                    version=version_db.version_number
                )
                # Delete etcd keys
                etcd_util.delete_function(
                    id,
                    version=version_db.version_number
                )
                # Delete function version packages. Versions is only supported
                # for package type function.
                self.storage_provider.delete(
                    func_db.project_id,
                    id,
                    None,
                    version=version_db.version_number
                )

            # Delete resources for function version 0(func_db.versions==[])
            self.engine_client.delete_function(id)
            etcd_util.delete_function(id)

            source = func_db.code['source']
            if source == constants.PACKAGE_FUNCTION:
                self.storage_provider.delete(func_db.project_id, id,
                                             func_db.code['md5sum'])

            # This will also delete function service mapping and function
            # versions as well.
            db_api.delete_function(id)

    @rest_utils.wrap_pecan_controller_exception
    @pecan.expose('json')
    def put(self, id, **kwargs):
        """Update function.

        - Function can not being used by job.
        - Function can not being executed.
        - (TODO)Function status should be changed so no execution will create
           when function is updating.
        """
        values = {}

        try:
            for key in UPDATE_ALLOWED:
                if kwargs.get(key) is not None:
                    if key == "code":
                        kwargs[key] = json.loads(kwargs[key])
                    values.update({key: kwargs[key]})
        except Exception as e:
            raise exc.InputException("Invalid input, %s" % str(e))

        LOG.info('Update function %s, params: %s', id, values)
        ctx = context.get_ctx()

        if values.get('timeout'):
            common.validate_int_in_range(
                'timeout', values['timeout'], CONF.resource_limits.min_timeout,
                CONF.resource_limits.max_timeout
            )

        db_update_only = set(['name', 'description', 'timeout'])
        if set(values.keys()).issubset(db_update_only):
            func_db = db_api.update_function(id, values)
        else:
            source = values.get('code', {}).get('source')
            md5sum = values.get('code', {}).get('md5sum')
            cpu = values.get('cpu')
            memory_size = values.get('memory_size')

            # Check cpu and memory_size values when updating.
            if cpu is not None:
                common.validate_int_in_range(
                    'cpu', values['cpu'], CONF.resource_limits.min_cpu,
                    CONF.resource_limits.max_cpu
                )
            if memory_size is not None:
                common.validate_int_in_range(
                    'memory', values['memory_size'],
                    CONF.resource_limits.min_memory,
                    CONF.resource_limits.max_memory
                )

            with db_api.transaction():
                pre_func = db_api.get_function(id)

                if len(pre_func.jobs) > 0:
                    raise exc.NotAllowedException(
                        'The function is still associated with running job(s).'
                    )

                pre_source = pre_func.code['source']
                pre_md5sum = pre_func.code.get('md5sum')

                if source and source != pre_source:
                    raise exc.InputException(
                        "The function code type can not be changed."
                    )

                if pre_source == constants.IMAGE_FUNCTION:
                    raise exc.InputException(
                        "The image type function code can not be changed."
                    )

                # Package type function. 'code' and 'entry' make sense only if
                # 'package' is provided
                package_updated = False
                if (pre_source == constants.PACKAGE_FUNCTION and
                        values.get('package') is not None):
                    if md5sum and md5sum == pre_md5sum:
                        raise exc.InputException(
                            "The function code checksum is not changed."
                        )

                    # Update the package data.
                    data = values['package'].file.read()
                    package_updated, md5sum = self.storage_provider.store(
                        ctx.projectid,
                        id,
                        data,
                        md5sum=md5sum
                    )
                    values.setdefault('code', {}).update(
                        {"md5sum": md5sum, "source": pre_source}
                    )
                    values.pop('package')

                # Swift type function
                if (pre_source == constants.SWIFT_FUNCTION and
                        "swift" in values.get('code', {})):
                    swift_info = values['code']["swift"]

                    if not (swift_info.get('container') or
                            swift_info.get('object')):
                        raise exc.InputException(
                            "Either container or object must be provided for "
                            "swift type function update."
                        )

                    new_swift_info = pre_func.code['swift']
                    new_swift_info.update(swift_info)

                    self._check_swift(
                        new_swift_info.get('container'),
                        new_swift_info.get('object')
                    )

                    values['code'] = {
                        "source": pre_source,
                        "swift": new_swift_info
                    }

                # Delete allocated resources in orchestrator and etcd.
                self.engine_client.delete_function(id)
                etcd_util.delete_function(id)

                func_db = db_api.update_function(id, values)

            # Delete the old function package if needed
            if package_updated:
                self.storage_provider.delete(ctx.projectid, id, pre_md5sum)

        pecan.response.status = 200
        return resources.Function.from_db_obj(func_db).to_dict()

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(
        None,
        types.uuid,
        body=resources.ScaleInfo,
        status_code=202
    )
    def scale_up(self, id, scale):
        """Scale up the containers for function execution.

        This is admin only operation. The load monitoring of function execution
        depends on the monitoring solution of underlying orchestrator.
        """
        acl.enforce('function:scale_up', context.get_ctx())

        func_db = db_api.get_function(id)
        params = scale.to_dict()

        LOG.info('Starting to scale up function %s, params: %s', id, params)

        self.engine_client.scaleup_function(
            id,
            runtime_id=func_db.runtime_id,
            count=params['count']
        )

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(
        None,
        types.uuid,
        body=resources.ScaleInfo,
        status_code=202
    )
    def scale_down(self, id, scale):
        """Scale down the containers for function execution.

        This is admin only operation. The load monitoring of function execution
        depends on the monitoring solution of underlying orchestrator.
        """
        acl.enforce('function:scale_down', context.get_ctx())

        db_api.get_function(id)
        workers = etcd_util.get_workers(id)
        params = scale.to_dict()
        if len(workers) <= 1:
            LOG.info('No need to scale down function %s', id)
            return

        LOG.info('Starting to scale down function %s, params: %s', id, params)
        self.engine_client.scaledown_function(id, count=params['count'])

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(None, types.uuid, status_code=202)
    def detach(self, id):
        """Detach the function from its underlying workers.

        This is admin only operation, which gives admin user a safe way to
        clean up the underlying resources allocated for the function.
        """
        acl.enforce('function:detach', context.get_ctx())

        db_api.get_function(id)
        LOG.info('Starting to detach function %s', id)

        # Delete allocated resources in orchestrator and etcd keys.
        self.engine_client.delete_function(id)
        etcd_util.delete_function(id)
