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
import json
import mock

from qinling import context
from qinling.db import api as db_api
from qinling.tests.unit.api import base
from qinling.utils import constants


class TestWebhookController(base.APITest):
    def setUp(self):
        super(TestWebhookController, self).setUp()
        db_func = self.create_function()
        self.func_id = db_func.id

    def test_crud(self):
        # Create
        body = {
            'function_id': self.func_id,
            'description': 'webhook test'
        }
        resp = self.app.post_json('/v1/webhooks', body)
        self.assertEqual(201, resp.status_int)
        webhook_id = resp.json.get('id')
        self.assertIn(self.qinling_endpoint, resp.json.get('webhook_url'))

        # Get
        resp = self.app.get('/v1/webhooks/%s' % webhook_id)
        self.assertEqual(200, resp.status_int)
        self._assertDictContainsSubset(resp.json, body)

        # List
        resp = self.app.get('/v1/webhooks')
        self.assertEqual(200, resp.status_int)
        actual = self._assert_single_item(
            resp.json['webhooks'], id=webhook_id
        )
        self._assertDictContainsSubset(actual, body)

        # Update
        resp = self.app.put_json(
            '/v1/webhooks/%s' % webhook_id,
            {'description': 'webhook test update'}
        )
        self.assertEqual(200, resp.status_int)

        expected = {
            'function_id': self.func_id,
            'description': 'webhook test update'
        }
        resp = self.app.get('/v1/webhooks/%s' % webhook_id)
        self.assertEqual(200, resp.status_int)
        self._assertDictContainsSubset(resp.json, expected)

        # Delete
        resp = self.app.delete('/v1/webhooks/%s' % webhook_id)
        self.assertEqual(204, resp.status_int)
        resp = self.app.get('/v1/webhooks/%s' % webhook_id, expect_errors=True)
        self.assertEqual(404, resp.status_int)

    def test_create_with_version(self):
        db_api.increase_function_version(self.func_id, 0)

        body = {
            'function_id': self.func_id,
            'function_version': 1,
            'description': 'webhook test'
        }
        resp = self.app.post_json('/v1/webhooks', body)

        self.assertEqual(201, resp.status_int)
        self.assertEqual(1, resp.json.get("function_version"))
        self.assertIsNone(resp.json.get("function_alias"))

    def test_create_with_alias(self):
        db_api.increase_function_version(self.func_id, 0)
        name = self.rand_name(name="alias", prefix=self.prefix)
        body = {
            'function_id': self.func_id,
            'function_version': 1,
            'name': name
        }
        db_api.create_function_alias(**body)

        webhook_body = {
            'function_alias': name,
            'description': 'webhook test'
        }
        resp = self.app.post_json('/v1/webhooks', webhook_body)

        self.assertEqual(201, resp.status_int)
        self.assertEqual(name, resp.json.get('function_alias'))
        self.assertIsNone(resp.json.get("function_id"))
        self.assertIsNone(resp.json.get("function_version"))

    def test_create_with_invalid_alias(self):
        body = {
            'function_alias': 'fake_alias',
            'description': 'webhook test'
        }

        resp = self.app.post_json('/v1/webhooks', body, expect_errors=True)

        self.assertEqual(404, resp.status_int)

    def test_create_without_required_params(self):
        resp = self.app.post(
            '/v1/webhooks',
            params={},
            expect_errors=True
        )

        self.assertEqual(400, resp.status_int)

    def test_update_with_version(self):
        db_api.increase_function_version(self.func_id, 0)
        webhook = self.create_webhook(self.func_id)

        self.assertIsNone(webhook.function_version)

        resp = self.app.put_json(
            '/v1/webhooks/%s' % webhook.id,
            {'function_version': 1}
        )

        self.assertEqual(200, resp.status_int)
        self.assertEqual(1, resp.json.get("function_version"))
        self.assertIsNone(resp.json.get("function_alias"))

    def test_update_only_description(self):
        db_api.increase_function_version(self.func_id, 0)
        webhook = self.create_webhook(self.func_id, function_version=1)

        self.assertEqual(1, webhook.function_version)

        resp = self.app.put_json(
            '/v1/webhooks/%s' % webhook.id,
            {'description': 'updated description'}
        )

        self.assertEqual(200, resp.status_int)
        self.assertEqual(1, resp.json.get("function_version"))
        self.assertEqual('updated description', resp.json.get("description"))

    def test_update_function_alias_1(self):
        # Create webhook using function alias
        db_api.increase_function_version(self.func_id, 0)
        name = self.rand_name(name="alias", prefix=self.prefix)
        body = {
            'function_id': self.func_id,
            'function_version': 1,
            'name': name
        }
        db_api.create_function_alias(**body)
        webhook = self.create_webhook(function_alias=name)

        db_api.increase_function_version(self.func_id, 1)
        new_name = self.rand_name(name="alias", prefix=self.prefix)
        body = {
            'function_id': self.func_id,
            'function_version': 2,
            'name': new_name
        }
        db_api.create_function_alias(**body)

        # Update webhook with the new alias
        resp = self.app.put_json(
            '/v1/webhooks/%s' % webhook.id,
            {'function_alias': new_name}
        )

        self.assertEqual(200, resp.status_int)
        self.assertEqual(new_name, resp.json.get("function_alias"))
        self.assertIsNone(resp.json.get("function_id"))
        self.assertIsNone(resp.json.get("function_version"))

    def test_update_function_alias_2(self):
        # Create webhook using function id
        db_api.increase_function_version(self.func_id, 0)
        webhook = self.create_webhook(function_id=self.func_id,
                                      function_version=1)

        db_api.increase_function_version(self.func_id, 1)
        alias_name = self.rand_name(name="alias", prefix=self.prefix)
        body = {
            'function_id': self.func_id,
            'function_version': 2,
            'name': alias_name
        }
        db_api.create_function_alias(**body)

        # Update webhook with function alias
        resp = self.app.put_json(
            '/v1/webhooks/%s' % webhook.id,
            {'function_alias': alias_name}
        )

        self.assertEqual(200, resp.status_int)
        self.assertEqual(alias_name, resp.json.get("function_alias"))
        self.assertIsNone(resp.json.get("function_id"))
        self.assertIsNone(resp.json.get("function_version"))

    @mock.patch("qinling.utils.openstack.keystone.create_trust_context")
    @mock.patch("qinling.utils.executions.create_execution")
    def test_invoke_with_function_id(self, mock_create_execution,
                                     mock_create_context):
        exec_mock = mock_create_execution.return_value
        exec_mock.id = "fake_id"
        webhook = self.create_webhook(function_id=self.func_id)

        resp = self.app.post_json('/v1/webhooks/%s/invoke' % webhook.id, {})
        context.set_ctx(self.ctx)

        self.assertEqual(202, resp.status_int)

        params = {
            'function_id': self.func_id,
            'function_version': None,
            'sync': False,
            'input': json.dumps({}),
            'description': constants.EXECUTION_BY_WEBHOOK % webhook.id
        }
        mock_create_execution.assert_called_once_with(mock.ANY, params)

    @mock.patch("qinling.utils.openstack.keystone.create_trust_context")
    @mock.patch("qinling.utils.executions.create_execution")
    def test_invoke_with_function_alias(self, mock_create_execution,
                                        mock_create_context):
        exec_mock = mock_create_execution.return_value
        exec_mock.id = "fake_id"

        db_api.increase_function_version(self.func_id, 0)
        alias_name = self.rand_name(name="alias", prefix=self.prefix)
        body = {
            'function_id': self.func_id,
            'function_version': 1,
            'name': alias_name
        }
        db_api.create_function_alias(**body)
        webhook = self.create_webhook(function_alias=alias_name)

        resp = self.app.post_json('/v1/webhooks/%s/invoke' % webhook.id, {})
        context.set_ctx(self.ctx)

        self.assertEqual(202, resp.status_int)

        params = {
            'function_id': self.func_id,
            'function_version': 1,
            'sync': False,
            'input': json.dumps({}),
            'description': constants.EXECUTION_BY_WEBHOOK % webhook.id
        }
        mock_create_execution.assert_called_once_with(mock.ANY, params)
