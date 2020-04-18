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
from unittest import mock
import uuid

from oslo_config import cfg

from qinling.db import api as db_api
from qinling import status
from qinling.tests.unit.api import base
from qinling.tests.unit import base as unit_base
from qinling.utils import constants


class TestFunctionController(base.APITest):
    def setUp(self):
        super(TestFunctionController, self).setUp()

        # Insert a runtime record in db for each test case. The data will be
        # removed automatically in tear down.
        db_runtime = self.create_runtime()
        self.runtime_id = db_runtime.id

    @mock.patch('qinling.storage.file_system.FileSystemStorage.store')
    def test_post(self, mock_store):
        mock_store.return_value = (True, 'fake_md5')

        with tempfile.NamedTemporaryFile() as f:
            body = {
                'name': self.rand_name('function', prefix=self.prefix),
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
                'code': {"source": "package", "md5sum": "fake_md5"},
                'timeout': cfg.CONF.resource_limits.default_timeout
            }
        )
        self._assertDictContainsSubset(resp.json, body)

    @mock.patch('qinling.storage.file_system.FileSystemStorage.store')
    def test_post_timeout(self, mock_store):
        mock_store.return_value = (True, 'fake_md5')

        with tempfile.NamedTemporaryFile() as f:
            body = {
                'runtime_id': self.runtime_id,
                'code': json.dumps({"source": "package"}),
                'timeout': 3
            }
            resp = self.app.post(
                '/v1/functions',
                params=body,
                upload_files=[('package', f.name, f.read())]
            )

        self.assertEqual(201, resp.status_int)
        self.assertEqual(3, resp.json['timeout'])

    def test_post_timeout_invalid(self):
        with tempfile.NamedTemporaryFile() as f:
            body = {
                'runtime_id': self.runtime_id,
                'code': json.dumps({"source": "package"}),
                'timeout': cfg.CONF.resource_limits.max_timeout + 1
            }
            resp = self.app.post(
                '/v1/functions',
                params=body,
                upload_files=[('package', f.name, f.read())],
                expect_errors=True
            )

        self.assertEqual(400, resp.status_int)
        self.assertIn(
            'timeout resource limitation not within the allowable range',
            resp.json['faultstring']
        )

    @mock.patch("qinling.utils.openstack.keystone.create_trust")
    @mock.patch('qinling.utils.openstack.keystone.get_swiftclient')
    @mock.patch('qinling.context.AuthHook.before')
    def test_post_from_swift(self, mock_auth, mock_client, mock_trust):
        self.override_config('auth_enable', True, group='pecan')

        swift_conn = mock.Mock()
        mock_client.return_value = swift_conn
        swift_conn.head_object.return_value = {
            'accept-ranges': 'bytes',
            'content-length': str(constants.MAX_PACKAGE_SIZE - 1)
        }
        mock_trust.return_value.id = str(uuid.uuid4())

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
        resp = self.app.post('/v1/functions', params=body)

        self.assertEqual(201, resp.status_int)

        body.update(
            {
                'entry': 'main.main',
                'code': {
                    "source": "swift",
                    "swift": {"container": "container", "object": "object"}
                }
            }
        )
        self._assertDictContainsSubset(resp.json, body)

    def test_post_swift_not_enough_params(self):
        body = {
            'name': 'swift_function',
            'code': json.dumps(
                {
                    "source": "swift",
                    "swift": {"container": "fake-container"}
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
        db_func = self.create_function(runtime_id=self.runtime_id)
        expected = {
            'id': db_func.id,
            "code": {"source": "package", "md5sum": "fake_md5"},
            "name": db_func.name,
            'entry': 'main.main',
            "project_id": unit_base.DEFAULT_PROJECT_ID,
            "cpu": cfg.CONF.resource_limits.default_cpu,
            "memory_size": cfg.CONF.resource_limits.default_memory,
            "timeout": cfg.CONF.resource_limits.default_timeout,
        }

        resp = self.app.get('/v1/functions/%s' % db_func.id)

        self.assertEqual(200, resp.status_int)
        self._assertDictContainsSubset(resp.json, expected)

    def test_get_all(self):
        db_func = self.create_function(runtime_id=self.runtime_id)
        expected = {
            'id': db_func.id,
            "name": db_func.name,
            'entry': 'main.main',
            "project_id": unit_base.DEFAULT_PROJECT_ID,
            "cpu": cfg.CONF.resource_limits.default_cpu,
            "memory_size": cfg.CONF.resource_limits.default_memory,
            "timeout": cfg.CONF.resource_limits.default_timeout,
        }

        resp = self.app.get('/v1/functions')

        self.assertEqual(200, resp.status_int)
        actual = self._assert_single_item(
            resp.json['functions'], id=db_func.id
        )
        self._assertDictContainsSubset(actual, expected)

    def test_put_name(self):
        db_func = self.create_function(runtime_id=self.runtime_id)

        resp = self.app.put_json(
            '/v1/functions/%s' % db_func.id, {'name': 'new_name'}
        )

        self.assertEqual(200, resp.status_int)
        self.assertEqual('new_name', resp.json['name'])

    def test_put_timeout(self):
        db_func = self.create_function(runtime_id=self.runtime_id)

        resp = self.app.put_json(
            '/v1/functions/%s' % db_func.id, {'timeout': 10}
        )

        self.assertEqual(200, resp.status_int)
        self.assertEqual(10, resp.json['timeout'])

    def test_put_timeout_invalid(self):
        db_func = self.create_function(runtime_id=self.runtime_id)

        # Check for type of cpu values.
        resp = self.app.put_json(
            '/v1/functions/%s' % db_func.id,
            {'timeout': cfg.CONF.resource_limits.max_timeout + 1},
            expect_errors=True
        )

        self.assertEqual(400, resp.status_int)
        self.assertIn(
            'timeout resource limitation not within the allowable range',
            resp.json['faultstring']
        )

    @mock.patch('qinling.utils.etcd_util.delete_function')
    @mock.patch('qinling.storage.file_system.FileSystemStorage.store')
    @mock.patch('qinling.storage.file_system.FileSystemStorage.delete')
    @mock.patch('qinling.rpc.EngineClient.delete_function')
    def test_put_package(self, mock_delete_func, mock_delete, mock_store,
                         mock_etcd_del):
        db_func = self.create_function(runtime_id=self.runtime_id)
        mock_store.return_value = (True, "fake_md5_changed")

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
        mock_delete.assert_called_once_with(unit_base.DEFAULT_PROJECT_ID,
                                            db_func.id, "fake_md5")

    @mock.patch('qinling.storage.file_system.FileSystemStorage.store')
    @mock.patch('qinling.rpc.EngineClient.delete_function')
    @mock.patch('qinling.utils.etcd_util.delete_function')
    @mock.patch('qinling.storage.file_system.FileSystemStorage.delete')
    def test_put_package_md5_not_change(self, file_delete_mock,
                                        etcd_delete_mock, function_delete_mock,
                                        store_mock):
        db_func = self.create_function(runtime_id=self.runtime_id)
        store_mock.return_value = (False, "fake_md5")

        with tempfile.NamedTemporaryFile() as f:
            resp = self.app.put(
                '/v1/functions/%s' % db_func.id,
                params={},
                upload_files=[('package', f.name, f.read())]
            )

        self.assertEqual(200, resp.status_int)
        self.assertEqual('fake_md5', resp.json['code'].get('md5sum'))
        function_delete_mock.assert_called_once_with(db_func.id)
        etcd_delete_mock.assert_called_once_with(db_func.id)
        self.assertFalse(file_delete_mock.called)

    def test_put_package_same_md5_provided(self):
        db_func = self.create_function(runtime_id=self.runtime_id)

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

    @mock.patch('qinling.rpc.EngineClient.delete_function')
    @mock.patch('qinling.utils.etcd_util.delete_function')
    @mock.patch('qinling.utils.openstack.swift.check_object')
    @mock.patch('qinling.context.AuthHook.before')
    def test_put_swift_function(self, mock_auth, mock_check, mock_etcd_delete,
                                mock_func_delete):
        self.override_config('auth_enable', True, group='pecan')
        mock_check.return_value = True

        db_func = self.create_function(
            runtime_id=self.runtime_id,
            code={
                "source": "swift",
                "swift": {"container": "fake-container", "object": "fake-obj"}
            }
        )

        body = {
            'code': json.dumps(
                {
                    "source": "swift",
                    "swift": {"object": "new-obj"}
                }
            ),
        }
        resp = self.app.put_json('/v1/functions/%s' % db_func.id, body)

        self.assertEqual(200, resp.status_int)
        swift_info = {
            'code': {
                "source": "swift",
                "swift": {"container": "fake-container", "object": "new-obj"}
            }
        }
        self._assertDictContainsSubset(resp.json, swift_info)

    @mock.patch('qinling.rpc.EngineClient.delete_function')
    @mock.patch('qinling.utils.etcd_util.delete_function')
    @mock.patch('qinling.utils.openstack.swift.check_object')
    @mock.patch('qinling.context.AuthHook.before')
    def test_put_swift_function_without_source(self, mock_auth, mock_check,
                                               mock_etcd_delete,
                                               mock_func_delete):
        self.override_config('auth_enable', True, group='pecan')
        mock_check.return_value = True

        db_func = self.create_function(
            runtime_id=self.runtime_id,
            code={
                "source": "swift",
                "swift": {"container": "fake-container", "object": "fake-obj"}
            }
        )

        body = {
            'code': json.dumps(
                {
                    "swift": {"object": "new-obj"}
                }
            ),
        }
        resp = self.app.put_json('/v1/functions/%s' % db_func.id, body)

        self.assertEqual(200, resp.status_int)
        swift_info = {
            'code': {
                "source": "swift",
                "swift": {"container": "fake-container", "object": "new-obj"}
            }
        }
        self._assertDictContainsSubset(resp.json, swift_info)

    def test_put_cpu_with_type_error(self):
        db_func = self.create_function(runtime_id=self.runtime_id)

        # Check for type of cpu values.
        resp = self.app.put_json(
            '/v1/functions/%s' % db_func.id, {'cpu': 'non-int'},
            expect_errors=True
        )

        self.assertEqual(400, resp.status_int)
        self.assertIn(
            'Invalid cpu resource specified. An integer is required.',
            resp.json['faultstring']
        )

    def test_put_cpu_with_overrun_error(self):
        db_func = self.create_function(runtime_id=self.runtime_id)

        # Check for cpu error with input out of range.
        resp = self.app.put_json(
            '/v1/functions/%s' % db_func.id, {'cpu': 0},
            expect_errors=True
        )

        self.assertEqual(400, resp.status_int)
        self.assertIn(
            'cpu resource limitation not within the allowable range',
            resp.json['faultstring']
        )

    @mock.patch('qinling.storage.file_system.FileSystemStorage.delete')
    @mock.patch('qinling.utils.etcd_util.delete_function')
    @mock.patch('qinling.rpc.EngineClient.delete_function')
    def test_put_cpu_and_memorysize(self, mock_delete_func, mock_etcd_del,
                                    mock_storage_delete):
        # Test for updating cpu/mem with good input values.
        db_func = self.create_function(runtime_id=self.runtime_id)

        req_body = {
            'cpu': str(cfg.CONF.resource_limits.default_cpu + 1),
            'memory_size': str(cfg.CONF.resource_limits.default_memory + 1)
        }

        resp = self.app.put_json('/v1/functions/%s' % db_func.id, req_body)

        self.assertEqual(200, resp.status_int)
        self.assertEqual(
            cfg.CONF.resource_limits.default_cpu + 1,
            resp.json['cpu']
        )
        self.assertEqual(
            cfg.CONF.resource_limits.default_memory + 1,
            resp.json['memory_size']
        )
        mock_delete_func.assert_called_once_with(db_func.id)
        mock_etcd_del.assert_called_once_with(db_func.id)
        self.assertFalse(mock_storage_delete.called)

    @mock.patch('qinling.utils.etcd_util.delete_function')
    @mock.patch('qinling.rpc.EngineClient.delete_function')
    @mock.patch('qinling.storage.file_system.FileSystemStorage.delete')
    def test_delete(self, mock_delete, mock_delete_func, mock_etcd_delete):
        db_func = self.create_function(runtime_id=self.runtime_id)
        resp = self.app.delete('/v1/functions/%s' % db_func.id)

        self.assertEqual(204, resp.status_int)
        mock_delete.assert_called_once_with(
            unit_base.DEFAULT_PROJECT_ID, db_func.id, "fake_md5"
        )
        mock_delete_func.assert_called_once_with(db_func.id)
        mock_etcd_delete.assert_called_once_with(db_func.id)

    def test_delete_with_running_job(self):
        db_func = self.create_function(runtime_id=self.runtime_id)
        self.create_job(
            function_id=db_func.id,
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
        db_func = self.create_function(runtime_id=self.runtime_id)
        self.create_webhook(function_id=db_func.id)

        resp = self.app.delete(
            '/v1/functions/%s' % db_func.id,
            expect_errors=True
        )

        self.assertEqual(403, resp.status_int)

    @mock.patch('qinling.utils.etcd_util.delete_function')
    @mock.patch('qinling.rpc.EngineClient.delete_function')
    @mock.patch('qinling.storage.file_system.FileSystemStorage.delete')
    def test_delete_with_versions(self, mock_package_delete,
                                  mock_engine_delete, mock_etcd_delete):
        db_func = self.create_function(runtime_id=self.runtime_id)
        func_id = db_func.id
        # Create two versions for the function
        db_api.increase_function_version(func_id, 0)
        db_api.increase_function_version(func_id, 1)

        resp = self.app.delete('/v1/functions/%s' % func_id)

        self.assertEqual(204, resp.status_int)

        self.assertEqual(3, mock_package_delete.call_count)
        self.assertEqual(3, mock_engine_delete.call_count)
        self.assertEqual(3, mock_etcd_delete.call_count)

        mock_package_delete.assert_has_calls(
            [
                mock.call(unit_base.DEFAULT_PROJECT_ID, func_id, None,
                          version=1),
                mock.call(unit_base.DEFAULT_PROJECT_ID, func_id, None,
                          version=2),
                mock.call(unit_base.DEFAULT_PROJECT_ID, func_id, "fake_md5")
            ]
        )

        mock_engine_delete.assert_has_calls(
            [
                mock.call(func_id, version=1),
                mock.call(func_id, version=2),
                mock.call(func_id)
            ]
        )

        mock_etcd_delete.assert_has_calls(
            [
                mock.call(func_id, version=1),
                mock.call(func_id, version=2),
                mock.call(func_id)
            ]
        )

    def test_delete_with_version_associate_webhook(self):
        db_func = self.create_function(runtime_id=self.runtime_id)
        func_id = db_func.id
        db_api.increase_function_version(func_id, 0)
        self.create_webhook(func_id, function_version=1)

        resp = self.app.delete(
            '/v1/functions/%s' % func_id,
            expect_errors=True
        )

        self.assertEqual(403, resp.status_int)

    def test_delete_with_alias(self):
        db_func = self.create_function(runtime_id=self.runtime_id)
        func_id = db_func.id
        name = self.rand_name(name="alias", prefix=self.prefix)
        body = {
            'function_id': func_id,
            'name': name
        }
        db_api.create_function_alias(**body)

        resp = self.app.delete(
            '/v1/functions/%s' % func_id,
            expect_errors=True
        )

        self.assertEqual(403, resp.status_int)

    @mock.patch('qinling.rpc.EngineClient.scaleup_function')
    def test_scale_up(self, scaleup_function_mock):
        db_func = self.create_function(runtime_id=self.runtime_id)

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
        db_func = self.create_function(runtime_id=self.runtime_id)
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
        db_func = self.create_function(runtime_id=self.runtime_id)
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
        db_func = self.create_function(runtime_id=self.runtime_id)

        resp = self.app.post(
            '/v1/functions/%s/detach' % db_func.id
        )

        self.assertEqual(202, resp.status_int)
        engine_delete_function_mock.assert_called_once_with(db_func.id)
        etcd_delete_function_mock.assert_called_once_with(db_func.id)
