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

from oslo_config import cfg
from oslo_log import log as logging
from pecan import rest
import wsmeext.pecan as wsme_pecan

from qinling.api.controllers.v1 import resources
from qinling.api.controllers.v1 import types
from qinling.engine import rpc
from qinling.utils import rest_utils

LOG = logging.getLogger(__name__)


class EnvironmentsController(rest.RestController):
    def __init__(self, *args, **kwargs):
        self.engine_client = rpc.get_engine_client()

        super(EnvironmentsController, self).__init__(*args, **kwargs)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Environment, types.uuid)
    def get(self, id):
        LOG.info("Fetch environment [id=%s]", id)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(
        resources.Environment,
        body=resources.Environment,
        status_code=201
    )
    def post(self, env):
        LOG.info("Create environment. [environment=%s]", env)

        self.engine_client.create_environment()

        return resources.Environment.from_dict(
            {'id': '123', 'name': 'python2.7'}
        )
