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

from qinling import context
from qinling.db import api as db_api
from qinling import exceptions as exc
from qinling.tests.unit.api import base
from qinling.tests.unit import base as unit_base


class TestFunctionAliasController(base.APITest):
    def setUp(self):
        super(TestFunctionAliasController, self).setUp()

        self.db_func = self.create_function()
        self.func_id = self.db_func.id

    def test_post(self):
        name = 'TestAlias'
        body = {'function_id': self.func_id,
                'name': name,
                'description': 'new alias'}

        resp = self.app.post_json('/v1/aliases', body)

        self.assertEqual(201, resp.status_int)
        self._assertDictContainsSubset(resp.json, body)

        context.set_ctx(self.ctx)

        func_alias_db = db_api.get_function_alias(name)
        self.assertEqual(name, func_alias_db.name)
        self.assertEqual(0, func_alias_db.function_version)

    def test_post_without_required_params(self):
        body = {}

        resp = self.app.post_json('/v1/aliases',
                                  body,
                                  expect_errors=True)

        self.assertEqual(400, resp.status_int)
        self.assertIn("Required param is missing.", resp.json['faultstring'])

    def test_get(self):
        name = 'TestAlias'
        function_version = 0
        body = {'function_id': self.func_id,
                'function_version': function_version,
                'name': name,
                'description': 'new alias'}
        db_api.create_function_alias(**body)

        resp = self.app.get('/v1/aliases/%s' % name)

        context.set_ctx(self.ctx)

        self.assertEqual(200, resp.status_int)
        self.assertEqual("new alias", resp.json.get('description'))

    def test_get_notfound(self):
        resp = self.app.get('/v1/aliases/%s' % 'fake_name',
                            expect_errors=True)

        self.assertEqual(404, resp.status_int)
        self.assertIn("FunctionAlias not found", resp.json['faultstring'])

    def test_get_all(self):
        name = self.rand_name(name="alias", prefix=self.prefix)
        body = {
            'function_id': self.func_id,
            'name': name
        }
        db_api.create_function_alias(**body)

        resp = self.app.get('/v1/aliases')

        self.assertEqual(200, resp.status_int)

        expected = {
            "name": name,
            'function_id': self.func_id,
            'function_version': 0,
            "project_id": unit_base.DEFAULT_PROJECT_ID,
        }
        actual = self._assert_single_item(resp.json['function_aliases'],
                                          name=name)
        self._assertDictContainsSubset(actual, expected)

    def test_delete(self):
        name = self.rand_name(name="alias", prefix=self.prefix)
        function_version = 0
        body = {'function_id': self.func_id,
                'function_version': function_version,
                'name': name,
                'description': 'new alias'}

        db_api.create_function_alias(**body)

        resp = self.app.delete('/v1/aliases/%s' % name)

        self.assertEqual(204, resp.status_int)

        context.set_ctx(self.ctx)

        self.assertRaises(exc.DBEntityNotFoundError,
                          db_api.get_function_alias,
                          name)

    def test_put(self):
        name = self.rand_name(name="alias", prefix=self.prefix)
        function_version = 0
        body = {'function_id': self.func_id,
                'function_version': function_version,
                'name': name,
                'description': 'new alias'}

        db_api.create_function_alias(**body)

        body['function_version'] = 1
        body['description'] = 'update alias'

        resp = self.app.put_json('/v1/aliases/%s' % name, body)

        self.assertEqual(200, resp.status_int)
        self._assertDictContainsSubset(resp.json, body)

    def test_put_without_optional_params(self):
        name = self.rand_name(name="alias", prefix=self.prefix)
        function_version = 1
        body = {'function_id': self.func_id,
                'function_version': function_version,
                'name': name,
                'description': 'new alias'}

        db_api.create_function_alias(**body)

        update_body = {}

        resp = self.app.put_json('/v1/aliases/%s' % name, update_body)

        self.assertEqual(200, resp.status_int)
        self._assertDictContainsSubset(resp.json, body)
