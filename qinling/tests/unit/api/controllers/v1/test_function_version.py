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

from datetime import datetime
from datetime import timedelta
import json
from unittest import mock


from qinling import context
from qinling.db import api as db_api
from qinling import status
from qinling.tests.unit.api import base
from qinling.tests.unit import base as unit_base


class TestFunctionVersionController(base.APITest):
    def setUp(self):
        super(TestFunctionVersionController, self).setUp()

        self.db_func = self.create_function()
        self.func_id = self.db_func.id

    @mock.patch('qinling.storage.file_system.FileSystemStorage.copy')
    @mock.patch('qinling.storage.file_system.FileSystemStorage.changed_since')
    @mock.patch('qinling.utils.etcd_util.get_function_version_lock')
    def test_post(self, mock_etcd_lock, mock_changed, mock_copy):
        lock = mock.Mock()
        mock_etcd_lock.return_value.__enter__.return_value = lock
        lock.is_acquired.return_value = True
        mock_changed.return_value = True

        # Getting function and versions needs to happen in a db transaction
        with db_api.transaction():
            func_db = db_api.get_function(self.func_id)
            self.assertEqual(0, len(func_db.versions))

        body = {'description': 'new version'}
        resp = self.app.post_json('/v1/functions/%s/versions' % self.func_id,
                                  body)

        self.assertEqual(201, resp.status_int)
        self._assertDictContainsSubset(resp.json, body)

        mock_changed.assert_called_once_with(unit_base.DEFAULT_PROJECT_ID,
                                             self.func_id, "fake_md5", 0)
        mock_copy.assert_called_once_with(unit_base.DEFAULT_PROJECT_ID,
                                          self.func_id, "fake_md5", 0)

        # We need to set context as it was removed after the API call
        context.set_ctx(self.ctx)

        with db_api.transaction():
            func_db = db_api.get_function(self.func_id)
            self.assertEqual(1, len(func_db.versions))

        # Verify the latest function version by calling API
        resp = self.app.get('/v1/functions/%s' % self.func_id)

        self.assertEqual(200, resp.status_int)
        self.assertEqual(1, resp.json.get('latest_version'))

    @mock.patch('qinling.storage.file_system.FileSystemStorage.changed_since')
    @mock.patch('qinling.utils.etcd_util.get_function_version_lock')
    def test_post_not_change(self, mock_etcd_lock, mock_changed):
        lock = mock.Mock()
        mock_etcd_lock.return_value.__enter__.return_value = lock
        lock.is_acquired.return_value = True
        mock_changed.return_value = False

        body = {'description': 'new version'}
        resp = self.app.post_json('/v1/functions/%s/versions' % self.func_id,
                                  body,
                                  expect_errors=True)

        self.assertEqual(403, resp.status_int)

    @mock.patch('qinling.utils.etcd_util.get_function_version_lock')
    def test_post_max_versions(self, mock_etcd_lock):
        lock = mock.Mock()
        mock_etcd_lock.return_value.__enter__.return_value = lock
        lock.is_acquired.return_value = True

        for i in range(10):
            self.create_function_version(i, function_id=self.func_id)

        resp = self.app.post_json('/v1/functions/%s/versions' % self.func_id,
                                  {},
                                  expect_errors=True)

        self.assertEqual(403, resp.status_int)

    @mock.patch('qinling.utils.etcd_util.get_function_version_lock')
    def test_post_etcd_lock_failed(self, mock_etcd_lock):
        lock = mock.Mock()
        mock_etcd_lock.return_value.__enter__.return_value = lock
        lock.is_acquired.return_value = False

        body = {'description': 'new version'}
        resp = self.app.post_json('/v1/functions/%s/versions' % self.func_id,
                                  body, expect_errors=True)

        self.assertEqual(500, resp.status_int)
        self.assertEqual("Internal server error.", resp.json['faultstring'])

    def test_get_all(self):
        db_api.increase_function_version(self.func_id, 0,
                                         description="version 1")

        resp = self.app.get('/v1/functions/%s/versions' % self.func_id)

        self.assertEqual(200, resp.status_int)
        actual = self._assert_single_item(resp.json['function_versions'],
                                          version_number=1)
        self.assertEqual("version 1", actual.get('description'))

    def test_get(self):
        db_api.increase_function_version(self.func_id, 0,
                                         description="version 1")

        resp = self.app.get('/v1/functions/%s/versions/1' % self.func_id)

        self.assertEqual(200, resp.status_int)
        self.assertEqual("version 1", resp.json.get('description'))

    @mock.patch('qinling.utils.etcd_util.delete_function')
    @mock.patch('qinling.rpc.EngineClient.delete_function')
    @mock.patch('qinling.storage.file_system.FileSystemStorage.delete')
    def test_delete(self, mock_package_delete, mock_engine_delete,
                    mock_etcd_delete):
        db_api.increase_function_version(self.func_id, 0,
                                         description="version 1")

        resp = self.app.delete('/v1/functions/%s/versions/1' % self.func_id)

        self.assertEqual(204, resp.status_int)
        mock_engine_delete.assert_called_once_with(self.func_id, version=1)
        mock_etcd_delete.assert_called_once_with(self.func_id, version=1)
        mock_package_delete.assert_called_once_with(
            unit_base.DEFAULT_PROJECT_ID,
            self.func_id, None, version=1
        )

        # We need to set context as it was removed after the API call
        context.set_ctx(self.ctx)

        with db_api.transaction():
            func_db = db_api.get_function(self.func_id)
            self.assertEqual(0, len(func_db.versions))
            self.assertEqual(0, func_db.latest_version)

    def test_delete_with_running_job(self):
        db_api.increase_function_version(self.func_id, 0,
                                         description="version 1")
        self.create_job(
            self.func_id,
            function_version=1,
            status=status.RUNNING,
            first_execution_time=datetime.utcnow(),
            next_execution_time=datetime.utcnow() + timedelta(hours=1),
        )

        resp = self.app.delete(
            '/v1/functions/%s/versions/1' % self.func_id,
            expect_errors=True
        )

        self.assertEqual(403, resp.status_int)

    def test_delete_with_webhook(self):
        db_api.increase_function_version(self.func_id, 0,
                                         description="version 1")
        self.create_webhook(self.func_id, function_version=1)

        resp = self.app.delete(
            '/v1/functions/%s/versions/1' % self.func_id,
            expect_errors=True
        )

        self.assertEqual(403, resp.status_int)

    def test_delete_with_alias(self):
        db_api.increase_function_version(self.func_id, 0,
                                         description="version 1")
        name = self.rand_name(name="alias", prefix=self.prefix)
        body = {
            'function_id': self.func_id,
            'function_version': 1,
            'name': name
        }
        db_api.create_function_alias(**body)

        resp = self.app.delete(
            '/v1/functions/%s/versions/1' % self.func_id,
            expect_errors=True
        )

        self.assertEqual(403, resp.status_int)

    @mock.patch('qinling.rpc.EngineClient.scaleup_function')
    def test_scale_up(self, scaleup_function_mock):
        db_api.increase_function_version(self.func_id, 0)

        body = {'count': 1}
        resp = self.app.post(
            '/v1/functions/%s/versions/1/scale_up' % self.func_id,
            params=json.dumps(body),
            content_type='application/json'
        )

        self.assertEqual(202, resp.status_int)
        scaleup_function_mock.assert_called_once_with(
            self.func_id,
            runtime_id=self.db_func.runtime_id,
            version=1,
            count=1
        )

    @mock.patch('qinling.utils.etcd_util.get_workers')
    @mock.patch('qinling.rpc.EngineClient.scaledown_function')
    def test_scale_down(self, scaledown_function_mock, get_workers_mock):
        db_api.increase_function_version(self.func_id, 0)
        get_workers_mock.return_value = [mock.Mock(), mock.Mock()]

        body = {'count': 1}
        resp = self.app.post(
            '/v1/functions/%s/versions/1/scale_down' % self.func_id,
            params=json.dumps(body),
            content_type='application/json'
        )

        self.assertEqual(202, resp.status_int)
        scaledown_function_mock.assert_called_once_with(self.func_id,
                                                        version=1, count=1)

    @mock.patch('qinling.utils.etcd_util.get_workers')
    @mock.patch('qinling.rpc.EngineClient.scaledown_function')
    def test_scale_down_no_need(self, scaledown_function_mock,
                                get_workers_mock):
        db_api.increase_function_version(self.func_id, 0)
        get_workers_mock.return_value = [mock.Mock()]

        body = {'count': 1}
        resp = self.app.post(
            '/v1/functions/%s/versions/1/scale_down' % self.func_id,
            params=json.dumps(body),
            content_type='application/json'
        )

        self.assertEqual(202, resp.status_int)
        scaledown_function_mock.assert_not_called()

    @mock.patch('qinling.utils.etcd_util.delete_function')
    @mock.patch('qinling.rpc.EngineClient.delete_function')
    def test_detach(self, engine_delete_function_mock,
                    etcd_delete_function_mock):
        db_api.increase_function_version(self.func_id, 0)

        resp = self.app.post(
            '/v1/functions/%s/versions/1/detach' % self.func_id
        )

        self.assertEqual(202, resp.status_int)
        engine_delete_function_mock.assert_called_once_with(self.func_id,
                                                            version=1)
        etcd_delete_function_mock.assert_called_once_with(self.func_id,
                                                          version=1)
