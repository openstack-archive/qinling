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
import os

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import strutils
import pecan
from pecan import rest
from webob.static import FileIter
import wsmeext.pecan as wsme_pecan

from qinling.api.controllers.v1 import resources
from qinling.api.controllers.v1 import types
from qinling import context
from qinling.db import api as db_api
from qinling import exceptions as exc
from qinling import rpc
from qinling.storage import base as storage_base
from qinling.utils.openstack import swift as swift_util
from qinling.utils import rest_utils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

POST_REQUIRED = set(['name', 'code'])
CODE_SOURCE = set(['package', 'swift', 'image'])
UPDATE_ALLOWED = set(['name', 'description', 'entry'])


class FunctionsController(rest.RestController):
    def __init__(self, *args, **kwargs):
        self.storage_provider = storage_base.load_storage_provider(CONF)
        self.engine_client = rpc.get_engine_client()
        self.type = 'function'

        super(FunctionsController, self).__init__(*args, **kwargs)

    @rest_utils.wrap_pecan_controller_exception
    @pecan.expose()
    def get(self, id):
        LOG.info("Fetch resource.", resource={'type': self.type, 'id': id})

        download = strutils.bool_from_string(
            pecan.request.GET.get('download', False)
        )
        func_db = db_api.get_function(id)
        ctx = context.get_ctx()

        if not download:
            pecan.override_template('json')
            return resources.Function.from_dict(func_db.to_dict()).to_dict()
        else:
            source = func_db.code['source']

            if source == 'package':
                f = self.storage_provider.retrieve(ctx.projectid, id)
            elif source == 'swift':
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
            pecan.response.headers['Content-Type'] = 'application/zip'
            pecan.response.headers['Content-Disposition'] = (
                'attachment; filename="%s"' % os.path.basename(func_db.name)
            )

    @rest_utils.wrap_pecan_controller_exception
    @pecan.expose('json')
    def post(self, **kwargs):
        LOG.info("Creating %s, params: %s", self.type, kwargs)

        # When using image to create function, runtime_id is not a required
        # param.
        if not POST_REQUIRED.issubset(set(kwargs.keys())):
            raise exc.InputException(
                'Required param is missing. Required: %s' % POST_REQUIRED
            )

        values = {
            'name': kwargs['name'],
            'description': kwargs.get('description'),
            'runtime_id': kwargs.get('runtime_id'),
            'code': json.loads(kwargs['code']),
            'entry': kwargs.get('entry', 'main.main'),
        }

        source = values['code'].get('source')
        if not source or source not in CODE_SOURCE:
            raise exc.InputException(
                'Invalid code source specified, available sources: %s' %
                ', '.join(CODE_SOURCE)
            )

        if source != 'image':
            if not kwargs.get('runtime_id'):
                raise exc.InputException('"runtime_id" must be specified.')

            runtime = db_api.get_runtime(kwargs['runtime_id'])
            if runtime.status != 'available':
                raise exc.InputException(
                    'Runtime %s is not available.' % kwargs['runtime_id']
                )

        store = False
        if values['code']['source'] == 'package':
            store = True
            data = kwargs['package'].file.read()
        elif values['code']['source'] == 'swift':
            # Auth needs to be enabled because qinling needs to check swift
            # object using user's credential.
            if not CONF.pecan.auth_enable:
                raise exc.InputException('Swift object not supported.')

            container = values['code']['swift'].get('container')
            object = values['code']['swift'].get('object')

            if not swift_util.check_object(container, object):
                raise exc.InputException('Object does not exist in Swift.')

        with db_api.transaction():
            func_db = db_api.create_function(values)

            if store:
                ctx = context.get_ctx()

                self.storage_provider.store(
                    ctx.projectid,
                    func_db.id,
                    data
                )

        pecan.response.status = 201
        return resources.Function.from_dict(func_db.to_dict()).to_dict()

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Functions)
    def get_all(self):
        LOG.info("Get all functions.")

        functions = [resources.Function.from_dict(db_model.to_dict())
                     for db_model in db_api.get_functions()]

        return resources.Functions(functions=functions)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(None, types.uuid, status_code=204)
    def delete(self, id):
        """Delete the specified function."""
        LOG.info("Delete resource.", resource={'type': self.type, 'id': id})

        with db_api.transaction():
            func_db = db_api.get_function(id)
            source = func_db.code['source']

            if source == 'package':
                self.storage_provider.delete(context.get_ctx().projectid, id)

            # Delete all resources created by orchestrator asynchronously.
            self.engine_client.delete_function(id)

            # This will also delete function service mapping as well.
            db_api.delete_function(id)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(
        resources.Function,
        types.uuid,
        body=resources.Function
    )
    def put(self, id, func):
        """Update function.

        Currently, we only support update name, description, entry.
        """
        values = {}
        for key in UPDATE_ALLOWED:
            if func.to_dict().get(key) is not None:
                values.update({key: func.to_dict()[key]})

        LOG.info('Update resource, params: %s', values,
                 resource={'type': self.type, 'id': id})

        with db_api.transaction():
            func_db = db_api.update_function(id, values)
            if 'entry' in values:
                # Update entry will delete allocated resources in orchestrator.
                db_api.delete_function_service_mapping(id)
                self.engine_client.delete_function(id)

        return resources.Function.from_dict(func_db.to_dict())
