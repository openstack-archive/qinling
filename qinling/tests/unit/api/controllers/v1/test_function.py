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
from qinling.utils import constants

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
        mock_store.return_value = 'fake_md5'

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

        body.update(
            {
                'entry': 'main.main',
                'code': {"source": "package", "md5sum": "fake_md5"}
            }
        )
        self._assertDictContainsSubset(resp.json, body)

    @mock.patch('qinling.utils.openstack.keystone.get_swiftclient')
    @mock.patch('qinling.context.AuthHook.before')
    def test_post_swift_size_exceed(self, mock_auth, mock_client):
        self.override_config('auth_enable', True, group='pecan')
        swift_conn = mock.Mock()
        mock_client.return_value = swift_conn
        swift_conn.head_object.return_value = {
            'accept-ranges': 'bytes',
            'content-length': str(constants.MAX_PACKAGE_SIZE + 1)
        }

        body = {
            'name': 'swift_function',
            'code': json.dumps(
                {
                    "source": "swift",
                    "swift": {"container": "container", "object": "object"}
                }
            ),
            'runtime_id': self.runtime_id,
        }
        resp = self.app.post(
            '/v1/functions',
            params=body,
            expect_errors=True
        )

        self.assertEqual(400, resp.status_int)

    def test_get(self):
        db_func = self.create_function(
            runtime_id=self.runtime_id, prefix=TEST_CASE_NAME
        )
        expected = {
            'id': db_func.id,
            "code": {"source": "package", "md5sum": "fake_md5"},
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
        mock_store.return_value = "fake_md5_changed"

        with tempfile.NamedTemporaryFile() as f:
            resp = self.app.put(
                '/v1/functions/%s' % db_func.id,
                params={},
                upload_files=[('package', f.name, f.read())]
            )

        self.assertEqual(200, resp.status_int)
        self.assertEqual(1, mock_store.call_count)
        self.assertEqual('fake_md5_changed', resp.json['code'].get('md5sum'))
        mock_delete_func.assert_called_once_with(db_func.id)
        mock_etcd_del.assert_called_once_with(db_func.id)

    def test_put_package_same_md5(self):
        db_func = self.create_function(
            runtime_id=self.runtime_id, prefix=TEST_CASE_NAME
        )

        with tempfile.NamedTemporaryFile() as f:
            resp = self.app.put(
                '/v1/functions/%s' % db_func.id,
                params={
                    "code": json.dumps(
                        {"md5sum": "fake_md5", "source": "package"}
                    )
                },
                upload_files=[('package', f.name, f.read())],
                expect_errors=True
            )

        self.assertEqual(400, resp.status_int)

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
            unit_base.DEFAULT_PROJECT_ID, db_func.id, "fake_md5"
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

    @mock.patch('qinling.rpc.EngineClient.scaleup_function')
    def test_scale_up(self, scaleup_function_mock):
        db_func = self.create_function(
            runtime_id=self.runtime_id, prefix=TEST_CASE_NAME
        )

        body = {'count': 1}
        resp = self.app.post(
            '/v1/functions/%s/scale_up' % db_func.id,
            params=json.dumps(body),
            content_type='application/json'
        )

        self.assertEqual(202, resp.status_int)
        scaleup_function_mock.assert_called_once_with(
            db_func.id, runtime_id=self.runtime_id, count=1)

    @mock.patch('qinling.utils.etcd_util.get_workers')
    @mock.patch('qinling.rpc.EngineClient.scaledown_function')
    def test_scale_down(self, scaledown_function_mock, get_workers_mock):
        db_func = self.create_function(
            runtime_id=self.runtime_id, prefix=TEST_CASE_NAME
        )
        get_workers_mock.return_value = [mock.Mock(), mock.Mock()]

        body = {'count': 1}
        resp = self.app.post(
            '/v1/functions/%s/scale_down' % db_func.id,
            params=json.dumps(body),
            content_type='application/json'
        )

        self.assertEqual(202, resp.status_int)
        scaledown_function_mock.assert_called_once_with(db_func.id, count=1)

    @mock.patch('qinling.utils.etcd_util.get_workers')
    @mock.patch('qinling.rpc.EngineClient.scaledown_function')
    def test_scale_down_no_need(
            self, scaledown_function_mock, get_workers_mock
    ):
        db_func = self.create_function(
            runtime_id=self.runtime_id, prefix=TEST_CASE_NAME
        )
        get_workers_mock.return_value = [mock.Mock()]

        body = {'count': 1}
        resp = self.app.post(
            '/v1/functions/%s/scale_down' % db_func.id,
            params=json.dumps(body),
            content_type='application/json'
        )

        self.assertEqual(202, resp.status_int)
        scaledown_function_mock.assert_not_called()

    @mock.patch('qinling.utils.etcd_util.delete_function')
    @mock.patch('qinling.rpc.EngineClient.delete_function')
    def test_detach(
            self, engine_delete_function_mock, etcd_delete_function_mock
    ):
        db_func = self.create_function(
            runtime_id=self.runtime_id, prefix=TEST_CASE_NAME
        )

        resp = self.app.post(
            '/v1/functions/%s/detach' % db_func.id
        )

        self.assertEqual(202, resp.status_int)
        engine_delete_function_mock.assert_called_once_with(db_func.id)
        etcd_delete_function_mock.assert_called_once_with(db_func.id)
