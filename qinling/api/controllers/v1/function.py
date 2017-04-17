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

from oslo_config import cfg
from oslo_log import log as logging
import pecan
from pecan import rest
import wsmeext.pecan as wsme_pecan

from qinling.api.controllers.v1 import resources
from qinling.api.controllers.v1 import types
from qinling import context
from qinling.db import api as db_api
from qinling import exceptions as exc
from qinling.storage import base as storage_base
from qinling.utils import rest_utils

LOG = logging.getLogger(__name__)

POST_REQUIRED = set(['name', 'runtime', 'code'])


class FunctionsController(rest.RestController):
    def __init__(self, *args, **kwargs):
        self.storage_provider = storage_base.load_storage_providers(cfg.CONF)

        super(FunctionsController, self).__init__(*args, **kwargs)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Function, types.uuid)
    def get(self, id):
        LOG.info("Fetch function [id=%s]", id)

        func_db = db_api.get_function(id)

        return resources.Function.from_dict(func_db.to_dict())

    def get_data(self, id):
        pass

    @rest_utils.wrap_pecan_controller_exception
    @pecan.expose()
    def post(self, **kwargs):
        LOG.info("Create function, params=%s", kwargs)

        if not POST_REQUIRED.issubset(set(kwargs.keys())):
            raise exc.InputException(
                'Required param is missing. Required: %s' % POST_REQUIRED
            )

        values = {
            'name': kwargs['name'],
            'runtime': kwargs['runtime'],
            'code': json.loads(kwargs['code']),
            'storage': 'local'
        }

        if values['code'].get('package', False):
            data = kwargs['package'].file.read()

        ctx = context.get_ctx()
        with db_api.transaction():
            func_db = db_api.create_function(values)

            self.storage_provider[values['storage']].store(
                ctx.projectid,
                values['name'],
                data
            )

        pecan.response.status = 201
        return resources.Function.from_dict(func_db.to_dict())

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Functions)
    def get_all(self):
        LOG.info("Get all functions.")

        funcs = resources.Functions()
        funcs.functions = []

        return funcs
