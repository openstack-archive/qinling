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

from oslo_log import log as logging
import pecan
from pecan import rest
import wsmeext.pecan as wsme_pecan

from qinling.api.controllers.v1 import resources
from qinling import exceptions as exc
from qinling.utils import rest_utils

LOG = logging.getLogger(__name__)

POST_REQUIRED = set(['name', 'runtime', 'code'])


class FunctionsController(rest.RestController):
    @rest_utils.wrap_pecan_controller_exception
    @pecan.expose()
    def post(self, **kwargs):
        """Create a new function.

        :param func: Function object.
        """
        LOG.info("Create function, params=%s", kwargs)

        if not POST_REQUIRED.issubset(set(kwargs.keys())):
            raise exc.InputException(
                'Required param is missing. Required: %s' % POST_REQUIRED
            )

        func = resources.Function()

        func.name = kwargs['name']
        func.runtime = kwargs['runtime']
        func.code = json.loads(kwargs['code'])

        if func.code.get('package', False):
            data = kwargs['package'].file.read()
            print data

        pecan.response.status = 201
        return func.to_json()

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Functions)
    def get_all(self):
        LOG.info("Get all functions.")

        funcs = resources.Functions()
        funcs.functions = []

        return funcs
