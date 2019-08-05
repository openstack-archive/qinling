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
from wsme import types as wtypes
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

UPDATE_ALLOWED = set(['function_id', 'function_version', 'description',
                      'function_alias'])


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
    @wsme_pecan.wsexpose(resources.Webhooks, bool, wtypes.text)
    def get_all(self, all_projects=False, project_id=None):
        project_id, all_projects = rest_utils.get_project_params(
            project_id, all_projects
        )
        if all_projects:
            acl.enforce('webhook:get_all:all_projects', context.get_ctx())

        filters = rest_utils.get_filters(
            project_id=project_id,
        )

        LOG.info("Get all %ss. filters=%s", self.type, filters)
        webhooks = []
        for i in db_api.get_webhooks(insecure=all_projects, **filters):
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
        if not (params.get("function_id") or params.get("function_alias")):
            raise exc.InputException(
                'Either function_alias or function_id must be provided.'
            )

        function_id = params.get('function_id', "")
        version = params.get('function_version', 0)
        function_alias = params.get('function_alias', "")

        if function_alias:
            alias_db = db_api.get_function_alias(function_alias)
            function_id = alias_db.function_id
            version = alias_db.function_version
            # If function_alias is provided, we don't store either functin id
            # or function version.
            params.update({'function_id': None,
                           'function_version': None})

        LOG.info("Creating %s, params: %s", self.type, params)

        # Even admin user can not expose normal user's function
        db_api.get_function(function_id, insecure=False)
        if version > 0:
            db_api.get_function_version(function_id, version)

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
        acl.enforce('webhook:update', context.get_ctx())

        values = {}
        for key in UPDATE_ALLOWED:
            if webhook.to_dict().get(key) is not None:
                values.update({key: webhook.to_dict()[key]})

        LOG.info('Update %s %s, params: %s', self.type, id, values)

        # Even admin user can not expose normal user's function
        webhook_db = db_api.get_webhook(id, insecure=False)
        pre_alias = webhook_db.function_alias
        pre_function_id = webhook_db.function_id
        pre_version = webhook_db.function_version

        new_alias = values.get("function_alias")
        new_function_id = values.get("function_id", pre_function_id)
        new_version = values.get("function_version", pre_version)

        function_id = pre_function_id
        version = pre_version
        if new_alias and new_alias != pre_alias:
            alias_db = db_api.get_function_alias(new_alias)
            function_id = alias_db.function_id
            version = alias_db.function_version
            # If function_alias is provided, we don't store either functin id
            # or function version.
            values.update({'function_id': None,
                           'function_version': None})
        elif new_function_id != pre_function_id or new_version != pre_version:
            function_id = new_function_id
            version = new_version
            values.update({"function_alias": None})

        db_api.get_function(function_id, insecure=False)
        if version and version > 0:
            db_api.get_function_version(function_id, version)

        webhook = db_api.update_webhook(id, values).to_dict()
        return resources.Webhook.from_dict(self._add_webhook_url(id, webhook))

    @rest_utils.wrap_pecan_controller_exception
    @pecan.expose('json')
    def invoke(self, id, **kwargs):
        with db_api.transaction():
            # The webhook url can be accessed without authentication, so
            # insecure is used here
            webhook_db = db_api.get_webhook(id, insecure=True)
            function_alias = webhook_db.function_alias

            if function_alias:
                alias = db_api.get_function_alias(function_alias,
                                                  insecure=True)
                function_id = alias.function_id
                function_version = alias.function_version
                function_db = db_api.get_function(function_id, insecure=True)
            else:
                function_db = webhook_db.function
                function_id = webhook_db.function_id
                function_version = webhook_db.function_version

            trust_id = function_db.trust_id
            project_id = function_db.project_id

        LOG.info(
            'Invoking function %s(version %s) by webhook %s',
            function_id, function_version, id
        )

        # Setup user context
        ctx = keystone_utils.create_trust_context(trust_id, project_id)
        context.set_ctx(ctx)

        params = {
            'function_id': function_id,
            'function_version': function_version,
            'sync': False,
            'input': json.dumps(kwargs),
            'description': constants.EXECUTION_BY_WEBHOOK % id
        }
        execution = executions.create_execution(self.engine_client, params)
        pecan.response.status = 202

        return {'execution_id': execution.id}
