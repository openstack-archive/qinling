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
from qinling import exceptions as exc
from qinling import rpc
from qinling.utils import rest_utils

LOG = logging.getLogger(__name__)


class RuntimesController(rest.RestController):
    def __init__(self, *args, **kwargs):
        self.engine_client = rpc.get_engine_client()

        super(RuntimesController, self).__init__(*args, **kwargs)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Runtime, types.uuid)
    def get(self, id):
        LOG.info("Fetch runtime [id=%s]", id)

        runtime_db = db_api.get_runtime(id)

        return resources.Runtime.from_dict(runtime_db.to_dict())

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Runtimes)
    def get_all(self):
        LOG.info("Get all runtimes.")

        runtimes = [resources.Runtime.from_dict(db_model.to_dict())
                    for db_model in db_api.get_runtimes()]

        return resources.Runtimes(runtimes=runtimes)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(
        resources.Runtime,
        body=resources.Runtime,
        status_code=201
    )
    def post(self, runtime):
        params = runtime.to_dict()

        LOG.info("Creating runtime. [runtime=%s]", params)

        params.update({'status': 'creating'})

        db_model = db_api.create_runtime(params)
        self.engine_client.create_runtime(db_model.id)

        return resources.Runtime.from_dict(db_model.to_dict())

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(None, types.uuid, status_code=204)
    def delete(self, id):
        """Delete runtime."""

        LOG.info("Delete runtime [id=%s]", id)

        with db_api.transaction():
            runtime_db = db_api.get_runtime(id)

            # Runtime can not be deleted if still associate with functions.
            funcs = db_api.get_functions(runtime_id={'eq': id})
            if len(funcs):
                raise exc.NotAllowedException(
                    'Runtime %s is still in use.' % id
                )

            runtime_db.status = 'deleting'

        # Clean related resources asynchronously
        self.engine_client.delete_runtime(id)
