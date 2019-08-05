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

import mock

from qinling.db import api as db_api
from qinling import exceptions as exc
from qinling import status
from qinling.tests.unit.api import base


class TestExecutionController(base.APITest):
    def setUp(self):
        super(TestExecutionController, self).setUp()

        db_func = self.create_function()
        self.func_id = db_func.id

    @mock.patch('qinling.rpc.EngineClient.create_execution')
    def test_create_with_function(self, mock_create_execution):
        body = {
            'function_id': self.func_id,
        }
        resp = self.app.post_json('/v1/executions', body)

        self.assertEqual(201, resp.status_int)

        resp = self.app.get('/v1/functions/%s' % self.func_id)

        self.assertEqual(1, resp.json.get('count'))

    @mock.patch('qinling.rpc.EngineClient.create_execution')
    def test_create_with_version(self, mock_rpc):
        db_api.increase_function_version(self.func_id, 0,
                                         description="version 1")
        body = {
            'function_id': self.func_id,
            'function_version': 1
        }

        resp = self.app.post_json('/v1/executions', body)
        self.assertEqual(201, resp.status_int)

        resp = self.app.get('/v1/functions/%s' % self.func_id)
        self.assertEqual(0, resp.json.get('count'))

        resp = self.app.get('/v1/functions/%s/versions/1' % self.func_id)
        self.assertEqual(1, resp.json.get('count'))

    @mock.patch('qinling.rpc.EngineClient.create_execution')
    def test_create_with_alias(self, mock_rpc):
        db_api.increase_function_version(self.func_id, 0,
                                         description="version 1")
        name = self.rand_name(name="alias", prefix=self.prefix)
        body = {
            'function_id': self.func_id,
            'function_version': 1,
            'name': name
        }
        db_api.create_function_alias(**body)

        execution_body = {
            'function_alias': name
        }
        resp = self.app.post_json('/v1/executions', execution_body)
        self.assertEqual(201, resp.status_int)
        self.assertEqual(name, resp.json.get('function_alias'))

        resp = self.app.get('/v1/functions/%s' % self.func_id)
        self.assertEqual(0, resp.json.get('count'))

        resp = self.app.get('/v1/functions/%s/versions/1' % self.func_id)
        self.assertEqual(1, resp.json.get('count'))

    def test_create_with_invalid_alias(self):
        body = {
            'function_alias': 'fake_alias',
        }

        resp = self.app.post_json('/v1/executions', body, expect_errors=True)

        self.assertEqual(404, resp.status_int)

    def test_create_without_required_params(self):
        resp = self.app.post(
            '/v1/executions',
            params={},
            expect_errors=True
        )

        self.assertEqual(400, resp.status_int)

    @mock.patch('qinling.rpc.EngineClient.create_execution')
    def test_create_rpc_error(self, mock_create_execution):
        mock_create_execution.side_effect = exc.QinlingException
        body = {
            'function_id': self.func_id,
        }
        resp = self.app.post_json('/v1/executions', body)

        self.assertEqual(201, resp.status_int)
        self.assertEqual(status.ERROR, resp.json.get('status'))

    @mock.patch('qinling.rpc.EngineClient.create_execution')
    def test_get(self, mock_create_execution):
        body = {
            'function_id': self.func_id,
        }
        resp = self.app.post_json('/v1/executions', body)

        self.assertEqual(201, resp.status_int)

        resp = self.app.get('/v1/executions/%s' % resp.json.get('id'))

        self.assertEqual(self.func_id, resp.json.get('function_id'))

    @mock.patch('qinling.rpc.EngineClient.create_execution')
    def test_get_all(self, mock_create_execution):
        body = {
            'function_id': self.func_id,
        }
        resp = self.app.post_json('/v1/executions', body)
        exec_id = resp.json.get('id')

        self.assertEqual(201, resp.status_int)

        resp = self.app.get('/v1/executions')

        self.assertEqual(200, resp.status_int)
        actual = self._assert_single_item(
            resp.json['executions'], id=exec_id
        )
        self._assertDictContainsSubset(actual, body)

    @mock.patch('qinling.rpc.EngineClient.create_execution')
    def test_get_all_filter(self, mock_create_execution):
        body = {
            'function_id': self.func_id,
        }
        resp = self.app.post_json('/v1/executions', body)
        exec_id = resp.json.get('id')
        self.assertEqual(201, resp.status_int)

        # Test filtering by 'function_id'
        resp = self.app.get('/v1/executions?function_id=%s' % self.func_id)
        self.assertEqual(200, resp.status_int)
        actual = self._assert_single_item(
            resp.json['executions'], id=exec_id
        )
        self._assertDictContainsSubset(actual, body)

        # Test filtering by 'status'
        resp = self.app.get(
            '/v1/executions?function_id=%s&status=running' % self.func_id
        )
        self.assertEqual(200, resp.status_int)
        self._assert_single_item(resp.json['executions'], id=exec_id)

    @mock.patch('qinling.rpc.EngineClient.create_execution')
    def test_delete(self, mock_create_execution):
        body = {
            'function_id': self.func_id,
        }
        resp = self.app.post_json('/v1/executions', body)
        exec_id = resp.json.get('id')

        resp = self.app.delete('/v1/executions/%s' % exec_id)

        self.assertEqual(204, resp.status_int)
