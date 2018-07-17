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
import pecan
from pecan import rest
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from qinling.api import access_control as acl
from qinling.api.controllers.v1 import resources
from qinling.api.controllers.v1 import types
from qinling import context
from qinling.db import api as db_api
from qinling import exceptions as exc
from qinling import rpc
from qinling.utils import executions
from qinling.utils import rest_utils

LOG = logging.getLogger(__name__)


class ExecutionLogController(rest.RestController):
    @rest_utils.wrap_pecan_controller_exception
    @pecan.expose(content_type='text/plain')
    def get_all(self, execution_id):
        LOG.info("Get logs for execution %s.", execution_id)
        execution_db = db_api.get_execution(execution_id)

        return execution_db.logs


class ExecutionsController(rest.RestController):
    log = ExecutionLogController()

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
        ctx = context.get_ctx()
        acl.enforce('execution:create', ctx)

        params = body.to_dict()
        if not (params.get("function_id") or params.get("function_alias")):
            raise exc.InputException(
                'Either function_alias or function_id must be provided.'
            )

        LOG.info("Creating %s. [params=%s]", self.type, params)

        db_model = executions.create_execution(self.engine_client, params)

        return resources.Execution.from_db_obj(db_model)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Executions, wtypes.text, bool, wtypes.text,
                         wtypes.text, wtypes.text)
    def get_all(self, function_id=None, all_projects=False, project_id=None,
                status=None, description=None):
        """Return a list of executions.

        :param function_id: Optional. Filtering executions by function_id.
        :param project_id: Optional. Admin user can query other projects
            resources, the param is ignored for normal user.
        :param all_projects: Optional. Get resources of all projects.
        :param status: Optional. Filter by execution status.
        :param description: Optional. Filter by description.
        """
        project_id, all_projects = rest_utils.get_project_params(
            project_id, all_projects
        )
        if all_projects:
            acl.enforce('execution:get_all:all_projects', context.get_ctx())

        filters = rest_utils.get_filters(
            function_id=function_id,
            project_id=project_id,
            status=status,
            description=description
        )
        LOG.info("Get all %ss. filters=%s", self.type, filters)

        db_execs = db_api.get_executions(insecure=all_projects, **filters)
        executions = [resources.Execution.from_db_obj(db_model)
                      for db_model in db_execs]

        return resources.Executions(executions=executions)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Execution, types.uuid)
    def get(self, id):
        LOG.info("Get resource.", resource={'type': self.type, 'id': id})

        execution_db = db_api.get_execution(id)

        return resources.Execution.from_db_obj(execution_db)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(None, types.uuid, status_code=204)
    def delete(self, id):
        """Delete the specified Execution."""
        LOG.info("Delete resource.", resource={'type': self.type, 'id': id})

        return db_api.delete_execution(id)
