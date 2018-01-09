# Copyright 2018 Catalyst IT Limited
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
import copy
import json

from oslo_log import log as logging
import pecan
from pecan import rest
import wsmeext.pecan as wsme_pecan

from qinling.api import access_control as acl
from qinling.api.controllers.v1 import resources
from qinling.api.controllers.v1 import types
from qinling import context
from qinling.db import api as db_api
from qinling import exceptions as exc
from qinling import rpc
from qinling.utils import constants
from qinling.utils import executions
from qinling.utils.openstack import keystone as keystone_utils
from qinling.utils import rest_utils

LOG = logging.getLogger(__name__)

POST_REQUIRED = set(['function_id'])
UPDATE_ALLOWED = set(['function_id', 'description'])


class WebhooksController(rest.RestController):
    _custom_actions = {
        'invoke': ['POST'],
    }

    def __init__(self, *args, **kwargs):
        self.type = 'webhook'
        self.engine_client = rpc.get_engine_client()
        self.qinling_endpoint = keystone_utils.get_qinling_endpoint()

        super(WebhooksController, self).__init__(*args, **kwargs)

    def _add_webhook_url(self, id, webhook):
        """Add webhook_url attribute for webhook.

        We generate the url dynamically in case the service url is changing.
        """
        res = copy.deepcopy(webhook)
        url = '/'.join(
            [self.qinling_endpoint.strip('/'), constants.CURRENT_VERSION,
             'webhooks', id, 'invoke']
        )
        res.update({'webhook_url': url})
        return res

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Webhook, types.uuid)
    def get(self, id):
        LOG.info("Get %s %s.", self.type, id)
        webhook = db_api.get_webhook(id).to_dict()
        return resources.Webhook.from_dict(self._add_webhook_url(id, webhook))

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Webhooks)
    def get_all(self):
        LOG.info("Get all %ss.", self.type)

        webhooks = []
        for i in db_api.get_webhooks():
            webhooks.append(
                resources.Webhook.from_dict(
                    self._add_webhook_url(i.id, i.to_dict())
                )
            )

        return resources.Webhooks(webhooks=webhooks)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(
        resources.Webhook,
        body=resources.Webhook,
        status_code=201
    )
    def post(self, webhook):
        acl.enforce('webhook:create', context.get_ctx())

        params = webhook.to_dict()
        if not POST_REQUIRED.issubset(set(params.keys())):
            raise exc.InputException(
                'Required param is missing. Required: %s' % POST_REQUIRED
            )

        LOG.info("Creating %s, params: %s", self.type, params)

        # Even admin user can not expose normal user's function
        db_api.get_function(params['function_id'], insecure=False)
        webhook_d = db_api.create_webhook(params).to_dict()

        return resources.Webhook.from_dict(
            self._add_webhook_url(webhook_d['id'], webhook_d)
        )

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(None, types.uuid, status_code=204)
    def delete(self, id):
        acl.enforce('webhook:delete', context.get_ctx())
        LOG.info("Delete %s %s.", self.type, id)
        db_api.delete_webhook(id)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(
        resources.Webhook,
        types.uuid,
        body=resources.Webhook
    )
    def put(self, id, webhook):
        """Update webhook.

        Currently, we only support update function_id.
        """
        acl.enforce('webhook:update', context.get_ctx())

        values = {}
        for key in UPDATE_ALLOWED:
            if webhook.to_dict().get(key) is not None:
                values.update({key: webhook.to_dict()[key]})

        LOG.info('Update %s %s, params: %s', self.type, id, values)

        if 'function_id' in values:
            # Even admin user can not expose normal user's function
            db_api.get_function(values['function_id'], insecure=False)

        webhook = db_api.update_webhook(id, values).to_dict()
        return resources.Webhook.from_dict(self._add_webhook_url(id, webhook))

    @rest_utils.wrap_pecan_controller_exception
    @pecan.expose('json')
    def invoke(self, id, **kwargs):
        with db_api.transaction():
            # The webhook url can be accessed without authentication, so
            # insecure is used here
            webhook_db = db_api.get_webhook(id, insecure=True)
            function_db = webhook_db.function
            trust_id = function_db.trust_id
            project_id = function_db.project_id

        LOG.info(
            'Invoking function %s by webhook %s',
            webhook_db.function_id, id
        )

        # Setup user context
        ctx = keystone_utils.create_trust_context(trust_id, project_id)
        context.set_ctx(ctx)

        params = {
            'function_id': webhook_db.function_id,
            'sync': False,
            'input': json.dumps(kwargs),
            'description': constants.EXECUTION_BY_WEBHOOK % id
        }
        execution = executions.create_execution(self.engine_client, params)
        pecan.response.status = 202

        return {'execution_id': execution.id}
