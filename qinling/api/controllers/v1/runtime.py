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

from qinling.api import access_control as acl
from qinling.api.controllers.v1 import resources
from qinling.api.controllers.v1 import types
from qinling import context
from qinling.db import api as db_api
from qinling import exceptions as exc
from qinling import rpc
from qinling import status
from qinling.utils import etcd_util
from qinling.utils import rest_utils

LOG = logging.getLogger(__name__)

POST_REQUIRED = set(['image'])
UPDATE_ALLOWED = set(['name', 'description', 'image'])


class RuntimesController(rest.RestController):
    _custom_actions = {'pool': ['GET']}

    def __init__(self, *args, **kwargs):
        self.engine_client = rpc.get_engine_client()
        self.type = 'runtime'

        super(RuntimesController, self).__init__(*args, **kwargs)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Runtime, types.uuid)
    def get(self, id):
        LOG.info("Get resource.", resource={'type': self.type, 'id': id})

        runtime_db = db_api.get_runtime(id)

        return resources.Runtime.from_db_obj(runtime_db)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Runtimes)
    def get_all(self):
        LOG.info("Get all %ss.", self.type)

        runtimes = [resources.Runtime.from_db_obj(db_model)
                    for db_model in db_api.get_runtimes()]

        return resources.Runtimes(runtimes=runtimes)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(
        resources.Runtime,
        body=resources.Runtime,
        status_code=201
    )
    def post(self, runtime):
        acl.enforce('runtime:create', context.get_ctx())

        params = runtime.to_dict()
        if 'trusted' not in params:
            params['trusted'] = True

        if not POST_REQUIRED.issubset(set(params.keys())):
            raise exc.InputException(
                'Required param is missing. Required: %s' % POST_REQUIRED
            )

        LOG.info("Creating %s, params: %s", self.type, params)

        params.update({'status': status.CREATING})

        db_model = db_api.create_runtime(params)
        self.engine_client.create_runtime(db_model.id)

        return resources.Runtime.from_db_obj(db_model)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(None, types.uuid, status_code=204)
    def delete(self, id):
        acl.enforce('runtime:delete', context.get_ctx())

        LOG.info("Delete resource.", resource={'type': self.type, 'id': id})

        with db_api.transaction():
            runtime_db = db_api.get_runtime(id)

            # Runtime can not be deleted if still associate with functions.
            funcs = db_api.get_functions(insecure=True, runtime_id={'eq': id})
            if len(funcs):
                raise exc.NotAllowedException(
                    'Runtime %s is still in use.' % id
                )

            runtime_db.status = status.DELETING

        # Clean related resources asynchronously
        self.engine_client.delete_runtime(id)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(
        resources.Runtime,
        types.uuid,
        body=resources.Runtime
    )
    def put(self, id, runtime):
        """Update runtime.

        Currently, we support update name, description, image. When
        updating image, send message to engine for asynchronous
        handling.
        """
        acl.enforce('runtime:update', context.get_ctx())

        values = {}
        for key in UPDATE_ALLOWED:
            if runtime.to_dict().get(key) is not None:
                values.update({key: runtime.to_dict()[key]})

        LOG.info('Update resource, params: %s', values,
                 resource={'type': self.type, 'id': id})

        image = values.get('image')

        with db_api.transaction():
            if image is not None:
                pre_runtime = db_api.get_runtime(id)
                if pre_runtime.status != status.AVAILABLE:
                    raise exc.RuntimeNotAvailableException(
                        'Runtime %s is not available.' % id
                    )

                pre_image = pre_runtime.image
                if pre_image != image:
                    # Ensure there is no function running in the runtime.
                    db_funcs = db_api.get_functions(
                        insecure=True, fields=['id'], runtime_id=id
                    )
                    func_ids = [func.id for func in db_funcs]

                    for id in func_ids:
                        if etcd_util.get_service_url(id):
                            raise exc.NotAllowedException(
                                'Runtime %s is still in use by functions.' % id
                            )

                    values['status'] = status.UPGRADING
                    self.engine_client.update_runtime(
                        id,
                        image=image,
                        pre_image=pre_image,
                    )

            runtime_db = db_api.update_runtime(id, values)

        return resources.Runtime.from_db_obj(runtime_db)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.RuntimePool, types.uuid)
    def pool(self, id):
        """Get the pool information for the runtime.

        This operation should be admin only.

        We don't check the runtime existence, because this function
        also helps us to check the underlying pool even after the runtime
        is already deleted.
        """
        acl.enforce('runtime_pool:get_all', context.get_ctx())

        LOG.info("Getting pool information for runtime %s.", id)
        capacity = self.engine_client.get_runtime_pool(id)
        pool_capacity = resources.RuntimePoolCapacity.from_dict(capacity)

        return resources.RuntimePool.from_dict(
            {"name": id, "capacity": pool_capacity}
        )
