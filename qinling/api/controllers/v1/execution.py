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

from oslo_log import log as logging
from pecan import rest
import wsmeext.pecan as wsme_pecan

from qinling.api.controllers.v1 import resources
from qinling.api.controllers.v1 import types
from qinling.db import api as db_api
from qinling import rpc
from qinling.utils import executions
from qinling.utils import rest_utils

LOG = logging.getLogger(__name__)


class ExecutionsController(rest.RestController):
    def __init__(self, *args, **kwargs):
        self.engine_client = rpc.get_engine_client()
        self.type = 'execution'

        super(ExecutionsController, self).__init__(*args, **kwargs)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(
        resources.Execution,
        body=resources.Execution,
        status_code=201
    )
    def post(self, body):
        params = body.to_dict()
        LOG.info("Creating %s. [params=%s]", self.type, params)

        db_model = executions.create_execution(self.engine_client, params)

        return resources.Execution.from_dict(db_model.to_dict())

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Executions)
    def get_all(self):
        LOG.info("Get all %ss.", self.type)

        executions = [resources.Execution.from_dict(db_model.to_dict())
                      for db_model in db_api.get_executions()]

        return resources.Executions(executions=executions)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Execution, types.uuid)
    def get(self, id):
        LOG.info("Fetch resource.", resource={'type': self.type, 'id': id})

        execution_db = db_api.get_execution(id)

        return resources.Execution.from_dict(execution_db.to_dict())

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(None, types.uuid, status_code=204)
    def delete(self, id):
        """Delete the specified Execution."""
        LOG.info("Delete resource.", resource={'type': self.type, 'id': id})

        return db_api.delete_execution(id)
