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
import pecan
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from qinling.api.controllers.v1 import execution
from qinling.api.controllers.v1 import function
from qinling.api.controllers.v1 import function_alias
from qinling.api.controllers.v1 import job
from qinling.api.controllers.v1 import resources
from qinling.api.controllers.v1 import runtime
from qinling.api.controllers.v1 import webhook


class RootResource(resources.Resource):
    """Root resource for API version 1.

    It references all other resources belonging to the API.
    """
    uri = wtypes.text


class Controller(object):
    """API root controller for version 1."""
    functions = function.FunctionsController()
    runtimes = runtime.RuntimesController()
    executions = execution.ExecutionsController()
    jobs = job.JobsController()
    webhooks = webhook.WebhooksController()
    aliases = function_alias.FunctionAliasesController()

    @wsme_pecan.wsexpose(RootResource)
    def index(self):
        return RootResource(uri='%s/%s' % (pecan.request.application_url,
                                           'v1'))
