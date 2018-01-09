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

from datetime import datetime
import json
import tempfile

import mock

from qinling import status
from qinling.tests.unit.api import base
from qinling.tests.unit import base as unit_base

TEST_CASE_NAME = 'TestFunctionController'


class TestFunctionController(base.APITest):
    def setUp(self):
        super(TestFunctionController, self).setUp()

        # Insert a runtime record in db for each test case. The data will be
        # removed automatically in tear down.
        db_runtime = self.create_runtime(prefix=TEST_CASE_NAME)
        self.runtime_id = db_runtime.id

    @mock.patch('qinling.storage.file_system.FileSystemStorage.store')
    def test_post(self, mock_store):
        with tempfile.NamedTemporaryFile() as f:
            body = {
                'name': self.rand_name('function', prefix=TEST_CASE_NAME),
                'code': json.dumps({"source": "package"}),
                'runtime_id': self.runtime_id,
            }
            resp = self.app.post(
                '/v1/functions',
                params=body,
                upload_files=[('package', f.name, f.read())]
            )

        self.assertEqual(201, resp.status_int)
        self.assertEqual(1, mock_store.call_count)

        body.update({'entry': 'main.main', 'code': {"source": "package"}})
        self._assertDictContainsSubset(resp.json, body)

    def test_get(self):
        db_func = self.create_function(
            runtime_id=self.runtime_id, prefix=TEST_CASE_NAME
        )
        expected = {
            'id': db_func.id,
            "code": {"source": "package"},
            "name": db_func.name,
            'entry': 'main.main',
            "project_id": unit_base.DEFAULT_PROJECT_ID,
        }

        resp = self.app.get('/v1/functions/%s' % db_func.id)

        self.assertEqual(200, resp.status_int)
        self._assertDictContainsSubset(resp.json, expected)

    def test_get_all(self):
        db_func = self.create_function(
            runtime_id=self.runtime_id, prefix=TEST_CASE_NAME
        )
        expected = {
            'id': db_func.id,
            "code": json.dumps({"source": "package"}),
            "name": db_func.name,
            'entry': 'main.main',
            "project_id": unit_base.DEFAULT_PROJECT_ID,
        }

        resp = self.app.get('/v1/functions')

        self.assertEqual(200, resp.status_int)
        actual = self._assert_single_item(
            resp.json['functions'], id=db_func.id
        )
        self._assertDictContainsSubset(actual, expected)

    def test_put_name(self):
        db_func = self.create_function(
            runtime_id=self.runtime_id, prefix=TEST_CASE_NAME
        )

        resp = self.app.put_json(
            '/v1/functions/%s' % db_func.id, {'name': 'new_name'}
        )

        self.assertEqual(200, resp.status_int)
        self.assertEqual('new_name', resp.json['name'])

    @mock.patch('qinling.utils.etcd_util.delete_function')
    @mock.patch('qinling.storage.file_system.FileSystemStorage.store')
    @mock.patch('qinling.rpc.EngineClient.delete_function')
    def test_put_package(self, mock_delete_func, mock_store, mock_etcd_del):
        db_func = self.create_function(
            runtime_id=self.runtime_id, prefix=TEST_CASE_NAME
        )

        with tempfile.NamedTemporaryFile() as f:
            resp = self.app.put(
                '/v1/functions/%s' % db_func.id,
                params={},
                upload_files=[('package', f.name, f.read())]
            )

        self.assertEqual(200, resp.status_int)
        self.assertEqual(1, mock_store.call_count)
        mock_delete_func.assert_called_once_with(db_func.id)
        mock_etcd_del.assert_called_once_with(db_func.id)

    @mock.patch('qinling.utils.etcd_util.delete_function')
    @mock.patch('qinling.rpc.EngineClient.delete_function')
    @mock.patch('qinling.storage.file_system.FileSystemStorage.delete')
    def test_delete(self, mock_delete, mock_delete_func, mock_etcd_delete):
        db_func = self.create_function(
            runtime_id=self.runtime_id, prefix=TEST_CASE_NAME
        )
        resp = self.app.delete('/v1/functions/%s' % db_func.id)

        self.assertEqual(204, resp.status_int)
        mock_delete.assert_called_once_with(
            unit_base.DEFAULT_PROJECT_ID, db_func.id
        )
        mock_delete_func.assert_called_once_with(db_func.id)
        mock_etcd_delete.assert_called_once_with(db_func.id)

    def test_delete_with_running_job(self):
        db_func = self.create_function(
            runtime_id=self.runtime_id, prefix=TEST_CASE_NAME
        )
        self.create_job(
            function_id=db_func.id,
            prefix=TEST_CASE_NAME,
            status=status.AVAILABLE,
            first_execution_time=datetime.utcnow(),
            next_execution_time=datetime.utcnow(),
            count=1
        )

        resp = self.app.delete(
            '/v1/functions/%s' % db_func.id,
            expect_errors=True
        )

        self.assertEqual(403, resp.status_int)

    def test_delete_with_webhook(self):
        db_func = self.create_function(
            runtime_id=self.runtime_id, prefix=TEST_CASE_NAME
        )
        self.create_webhook(function_id=db_func.id, prefix=TEST_CASE_NAME)

        resp = self.app.delete(
            '/v1/functions/%s' % db_func.id,
            expect_errors=True
        )

        self.assertEqual(403, resp.status_int)
