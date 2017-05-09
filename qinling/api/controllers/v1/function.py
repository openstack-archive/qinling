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
from qinling.storage import base as storage_base
from qinling.utils import rest_utils

LOG = logging.getLogger(__name__)

POST_REQUIRED = set(['name', 'runtime_id', 'code'])


class FunctionsController(rest.RestController):
    def __init__(self, *args, **kwargs):
        self.storage_provider = storage_base.load_storage_provider(cfg.CONF)

        super(FunctionsController, self).__init__(*args, **kwargs)

    @rest_utils.wrap_pecan_controller_exception
    @pecan.expose()
    def get(self, id):
        LOG.info("Fetch function [id=%s]", id)

        download = strutils.bool_from_string(
            pecan.request.GET.get('download', False)
        )
        func_db = db_api.get_function(id)
        ctx = context.get_ctx()

        if not download:
            pecan.override_template('json')
            return resources.Function.from_dict(func_db.to_dict()).to_dict()
        else:
            f = self.storage_provider.retrieve(
                ctx.projectid,
                id,
            )

            pecan.response.app_iter = FileIter(f)
            pecan.response.headers['Content-Type'] = 'application/zip'
            pecan.response.headers['Content-Disposition'] = (
                'attachment; filename="%s"' % os.path.basename(f.name)
            )

    @rest_utils.wrap_pecan_controller_exception
    @pecan.expose('json')
    def post(self, **kwargs):
        LOG.info("Creating function, params=%s", kwargs)

        if not POST_REQUIRED.issubset(set(kwargs.keys())):
            raise exc.InputException(
                'Required param is missing. Required: %s' % POST_REQUIRED
            )

        runtime = db_api.get_runtime(kwargs['runtime_id'])
        if runtime.status != 'available':
            raise exc.InputException(
                'Runtime %s not available.' % kwargs['runtime_id']
            )

        values = {
            'name': kwargs['name'],
            'description': kwargs.get('description', None),
            'runtime_id': kwargs['runtime_id'],
            'code': json.loads(kwargs['code']),
            'entry': kwargs.get('entry', 'main'),
        }

        if values['code'].get('package', False):
            data = kwargs['package'].file.read()

        ctx = context.get_ctx()

        with db_api.transaction():
            func_db = db_api.create_function(values)

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
        LOG.info("Delete function [id=%s]", id)

        with db_api.transaction():
            db_api.delete_function(id)

            self.storage_provider.delete(context.get_ctx().projectid, id)
