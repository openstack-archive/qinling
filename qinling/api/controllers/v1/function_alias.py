# Copyright 2018 OpenStack Foundation.
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
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from qinling.api import access_control as acl
from qinling.api.controllers.v1 import resources
from qinling import context
from qinling.db import api as db_api
from qinling import exceptions as exc
from qinling.utils import rest_utils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

POST_REQUIRED = set(['name', 'function_id'])
UPDATE_ALLOWED = set(['function_id', 'function_version', 'description'])


class FunctionAliasesController(rest.RestController):
    def __init__(self, *args, **kwargs):
        self.type = 'function_alias'

        super(FunctionAliasesController, self).__init__(*args, **kwargs)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(
        resources.FunctionAlias,
        body=resources.FunctionAlias,
        status_code=201
    )
    def post(self, body):
        """Create a new alias for the specified function.

        The supported body params:
            - function_id: Required. Function id the alias points to.
            - name: Required. Alias name, must be unique within the project.
            - function_version: Optional. Version number the alias points to.
            - description: Optional. The description of the new alias.
        """
        ctx = context.get_ctx()
        acl.enforce('function_alias:create', ctx)

        params = body.to_dict()
        if not POST_REQUIRED.issubset(set(params.keys())):
            raise exc.InputException(
                'Required param is missing. Required: %s' % POST_REQUIRED
            )
        LOG.info("Creating Alias, params: %s", params)

        values = {
            'function_id': params.get('function_id'),
            'name': params.get('name'),
            'function_version': params.get('function_version'),
            'description': params.get('description'),
        }

        alias = db_api.create_function_alias(**values)

        LOG.info("New alias created.")
        return resources.FunctionAlias.from_db_obj(alias)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.FunctionAlias, wtypes.text)
    def get(self, alias_name):
        acl.enforce('function_alias:get', context.get_ctx())
        LOG.info("Getting function alias  %s.", alias_name)

        alias = db_api.get_function_alias(alias_name)

        return resources.FunctionAlias.from_db_obj(alias)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.FunctionAliases, bool, wtypes.text)
    def get_all(self, all_projects=False, project_id=None):
        """Get all the function aliases.

        :param project_id: Optional. Admin user can query other projects
            resources, the param is ignored for normal user.
        :param all_projects: Optional. Get resources of all projects.
        """
        ctx = context.get_ctx()
        project_id, all_projects = rest_utils.get_project_params(
            project_id, all_projects
        )
        if all_projects:
            acl.enforce('function_version:get_all:all_projects', ctx)

        filters = rest_utils.get_filters(project_id=project_id)

        LOG.info("Get all function aliases. filters=%s", filters)

        db_aliases = db_api.get_function_aliases(
            insecure=all_projects, **filters)
        aliases = [resources.FunctionAlias.from_db_obj(db_model)
                   for db_model in db_aliases]

        return resources.FunctionAliases(function_aliases=aliases)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=204)
    def delete(self, alias_name):
        """Delete a specific alias.

        """
        ctx = context.get_ctx()
        acl.enforce('function_alias:delete', ctx)
        LOG.info("Deleting alias %s.", alias_name)

        db_api.delete_function_alias(alias_name)

        LOG.info("Alias %s deleted.", alias_name)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(
        resources.FunctionAlias,
        wtypes.text,
        body=resources.FunctionAlias,
    )
    def put(self, alias_name, body):
        """Update alias for the specified function.

        The supported body params:
            - function_id: Optional. Function id the alias point to.
            - function_version: Optional. Version number the alias point to.
            - description: Optional. The description of the alias.
        """
        ctx = context.get_ctx()
        acl.enforce('function_alias:update', ctx)

        params = body.to_dict()
        values = {}
        for key in UPDATE_ALLOWED:
            if params.get(key) is not None:
                values.update({key: params[key]})
        LOG.info("Updating Alias %s, params: %s", alias_name, values)

        alias = db_api.update_function_alias(alias_name, **values)

        LOG.info("Alias %s updated.", alias_name)
        return resources.FunctionAlias.from_db_obj(alias)
