# Copyright 2018 AWCloud Software Co., Ltd.
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

from unittest import mock

from oslo_config import cfg

from qinling.db import api as db_api
from qinling.engine import default_engine
from qinling import exceptions as exc
from qinling import status
from qinling.tests.unit import base
from qinling.utils import common
from qinling.utils import constants


class TestDefaultEngine(base.DbTestCase):
    def setUp(self):
        super(TestDefaultEngine, self).setUp()
        self.orchestrator = mock.Mock()
        self.qinling_endpoint = 'http://127.0.0.1:7070'
        self.default_engine = default_engine.DefaultEngine(
            self.orchestrator, self.qinling_endpoint
        )
        self.rlimit = {
            'cpu': cfg.CONF.resource_limits.default_cpu,
            'memory_size': cfg.CONF.resource_limits.default_memory
        }

    def _create_running_executions(self, function_id, num):
        for _ in range(num):
            self.create_execution(function_id=function_id)

    def test_create_runtime(self):
        runtime = self.create_runtime()
        runtime_id = runtime.id
        # Set status to verify it is changed during creation.
        db_api.update_runtime(runtime_id, {'status': status.CREATING})

        self.default_engine.create_runtime(mock.Mock(), runtime_id)

        self.orchestrator.create_pool.assert_called_once_with(
            runtime_id, runtime.image, trusted=True)

        runtime = db_api.get_runtime(runtime_id)
        self.assertEqual(status.AVAILABLE, runtime.status)

    def test_create_runtime_failed(self):
        runtime = self.create_runtime()
        runtime_id = runtime.id
        # Set status to verify it is changed during creation.
        db_api.update_runtime(runtime_id, {'status': status.CREATING})
        self.orchestrator.create_pool.side_effect = RuntimeError

        self.default_engine.create_runtime(mock.Mock(), runtime_id)

        self.orchestrator.create_pool.assert_called_once_with(
            runtime_id, runtime.image, trusted=True)
        runtime = db_api.get_runtime(runtime_id)
        self.assertEqual(status.ERROR, runtime.status)

    def test_delete_runtime(self):
        runtime = self.create_runtime()
        runtime_id = runtime.id

        self.default_engine.delete_runtime(mock.Mock(), runtime_id)

        self.orchestrator.delete_pool.assert_called_once_with(
            runtime_id)
        self.assertRaisesRegex(
            exc.DBEntityNotFoundError,
            "^Runtime not found \[id=%s\]$" % runtime_id,
            db_api.get_runtime, runtime_id)

    def test_update_runtime(self):
        runtime = self.create_runtime()
        runtime_id = runtime.id
        # Set status to verify it is changed during update.
        db_api.update_runtime(runtime_id, {'status': status.UPGRADING})
        image = self.rand_name('new_image', prefix=self.prefix)
        pre_image = self.rand_name('pre_image', prefix=self.prefix)
        self.orchestrator.update_pool.return_value = True

        self.default_engine.update_runtime(
            mock.Mock(), runtime_id, image, pre_image)

        self.orchestrator.update_pool.assert_called_once_with(
            runtime_id, image=image)
        runtime = db_api.get_runtime(runtime_id)
        self.assertEqual(runtime.status, status.AVAILABLE)

    def test_update_runtime_rollbacked(self):
        runtime = self.create_runtime()
        runtime_id = runtime.id
        # Set status to verify it is changed during update.
        db_api.update_runtime(runtime_id, {'status': status.UPGRADING})
        image = self.rand_name('new_image', prefix=self.prefix)
        pre_image = self.rand_name('pre_image', prefix=self.prefix)
        self.orchestrator.update_pool.return_value = False

        self.default_engine.update_runtime(
            mock.Mock(), runtime_id, image, pre_image)

        self.orchestrator.update_pool.assert_called_once_with(
            runtime_id, image=image)
        runtime = db_api.get_runtime(runtime_id)
        self.assertEqual(runtime.image, pre_image)
        self.assertEqual(runtime.status, status.AVAILABLE)

    @mock.patch('qinling.engine.default_engine.DefaultEngine.scaleup_function')
    @mock.patch('qinling.utils.etcd_util.get_workers')
    @mock.patch('qinling.utils.etcd_util.get_worker_lock')
    def test_function_load_check_no_worker(self, mock_getlock, mock_getworkers,
                                           mock_scaleup):
        function_id = common.generate_unicode_uuid()
        runtime_id = common.generate_unicode_uuid()
        lock = mock.Mock()
        lock.is_acquired.return_value = True
        mock_getlock.return_value.__enter__.return_value = lock
        mock_getworkers.return_value = []

        self.default_engine.function_load_check(function_id, 0, runtime_id)

        mock_getworkers.assert_called_once_with(function_id, 0)
        mock_scaleup.assert_called_once_with(None, function_id, 0, runtime_id,
                                             1)

    @mock.patch('qinling.engine.default_engine.DefaultEngine.scaleup_function')
    @mock.patch('qinling.utils.etcd_util.get_workers')
    @mock.patch('qinling.utils.etcd_util.get_worker_lock')
    def test_function_load_check_scaleup(self, mock_getlock, mock_getworkers,
                                         mock_scaleup):
        function = self.create_function()
        function_id = function.id
        runtime_id = function.runtime_id
        lock = mock.Mock()
        lock.is_acquired.return_value = True
        mock_getlock.return_value.__enter__.return_value = lock

        # The default concurrency is 3, we use 4 running executions against
        # 1 worker so that there will be a scaling up.
        mock_getworkers.return_value = ['worker1']
        self._create_running_executions(function_id, 4)

        self.default_engine.function_load_check(function_id, 0, runtime_id)

        mock_getworkers.assert_called_once_with(function_id, 0)
        mock_scaleup.assert_called_once_with(None, function_id, 0, runtime_id,
                                             1)

    @mock.patch('qinling.engine.default_engine.DefaultEngine.scaleup_function')
    @mock.patch('qinling.utils.etcd_util.get_workers')
    @mock.patch('qinling.utils.etcd_util.get_worker_lock')
    def test_function_load_check_not_scaleup(self, mock_getlock,
                                             mock_getworkers, mock_scaleup):
        function = self.create_function()
        function_id = function.id
        runtime_id = function.runtime_id
        lock = mock.Mock()
        lock.is_acquired.return_value = True
        mock_getlock.return_value.__enter__.return_value = lock

        # The default concurrency is 3, we use 3 running executions against
        # 1 worker so that there won't be a scaling up.
        mock_getworkers.return_value = ['worker1']
        self._create_running_executions(function_id, 3)

        self.default_engine.function_load_check(function_id, 0, runtime_id)

        mock_getworkers.assert_called_once_with(function_id, 0)
        mock_scaleup.assert_not_called()

    @mock.patch('qinling.utils.etcd_util.get_workers')
    @mock.patch('qinling.utils.etcd_util.get_worker_lock')
    def test_function_load_check_lock_wait(self, mock_getlock,
                                           mock_getworkers):
        function = self.create_function()
        function_id = function.id
        runtime_id = function.runtime_id
        lock = mock.Mock()
        mock_getlock.return_value.__enter__.return_value = lock
        # Lock is acquired upon the third try.
        lock.is_acquired.side_effect = [False, False, True]
        mock_getworkers.return_value = ['worker1']
        self._create_running_executions(function_id, 3)

        self.default_engine.function_load_check(function_id, 0, runtime_id)

        self.assertEqual(3, lock.is_acquired.call_count)
        mock_getworkers.assert_called_once_with(function_id, 0)

    @mock.patch('qinling.utils.etcd_util.get_worker_lock')
    def test_function_load_check_failed_to_get_worker_lock(self, mock_getlock):
        function = self.create_function()
        function_id = function.id
        runtime_id = function.runtime_id
        function_version = 0
        lock = mock.Mock()
        # Lock is never acquired.
        lock.is_acquired.return_value = False
        mock_getlock.return_value.__enter__.return_value = lock

        self.assertRaisesRegex(
            exc.EtcdLockException,
            "^Etcd: failed to get worker lock for function %s"
            "\(version %s\)\.$" % (function_id, function_version),
            self.default_engine.function_load_check,
            function_id, function_version, runtime_id
        )

    @mock.patch('qinling.utils.etcd_util.get_service_url')
    def test_create_execution_image_type_function(self, mock_svc_url):
        """Create 2 executions for an image type function."""
        function = self.create_function()
        function_id = function.id
        runtime_id = function.runtime_id
        db_api.update_function(
            function_id,
            {
                'code': {
                    'source': constants.IMAGE_FUNCTION,
                    'image': self.rand_name('image', prefix=self.prefix)
                }
            }
        )
        function = db_api.get_function(function_id)
        execution_1 = self.create_execution(function_id=function_id)
        execution_1_id = execution_1.id
        execution_2 = self.create_execution(function_id=function_id)
        execution_2_id = execution_2.id
        mock_svc_url.return_value = None
        self.orchestrator.prepare_execution.return_value = (
            mock.Mock(), None)
        self.orchestrator.run_execution.side_effect = [
            (True, {'duration': 5, 'logs': 'fake log'}),
            (False, {'duration': 0, 'output': 'Function execution failed.'})
        ]

        # Create two executions, with different results
        self.default_engine.create_execution(
            mock.Mock(), execution_1_id, function_id, 0, runtime_id
        )
        self.default_engine.create_execution(
            mock.Mock(), execution_2_id, function_id, 0, runtime_id,
            input='input'
        )

        get_service_url_calls = [
            mock.call(function_id, 0), mock.call(function_id, 0)
        ]
        mock_svc_url.assert_has_calls(get_service_url_calls)

        prepare_calls = [
            mock.call(function_id,
                      0,
                      rlimit=self.rlimit,
                      image=function.code['image'],
                      identifier=mock.ANY,
                      labels=None,
                      input=None),
            mock.call(function_id,
                      0,
                      rlimit=self.rlimit,
                      image=function.code['image'],
                      identifier=mock.ANY,
                      labels=None,
                      input='input')
        ]
        self.orchestrator.prepare_execution.assert_has_calls(prepare_calls)

        run_calls = [
            mock.call(execution_1_id,
                      function_id,
                      0,
                      rlimit=None,
                      input=None,
                      identifier=mock.ANY,
                      service_url=None,
                      entry=function.entry,
                      trust_id=function.trust_id,
                      timeout=function.timeout),
            mock.call(execution_2_id,
                      function_id,
                      0,
                      rlimit=None,
                      input='input',
                      identifier=mock.ANY,
                      service_url=None,
                      entry=function.entry,
                      trust_id=function.trust_id,
                      timeout=function.timeout)
        ]
        self.orchestrator.run_execution.assert_has_calls(run_calls)

        execution_1 = db_api.get_execution(execution_1_id)
        execution_2 = db_api.get_execution(execution_2_id)

        self.assertEqual(status.SUCCESS, execution_1.status)
        self.assertEqual('fake log', execution_1.logs)
        self.assertEqual({"duration": 5}, execution_1.result)
        self.assertEqual(status.FAILED, execution_2.status)
        self.assertEqual('', execution_2.logs)
        self.assertEqual(
            {'duration': 0, 'output': 'Function execution failed.'},
            execution_2.result
        )

    @mock.patch('qinling.utils.etcd_util.get_service_url')
    def test_create_execution_prepare_execution_exception(
            self,
            etcd_util_get_service_url_mock
    ):
        """test_create_execution_prepare_execution_exception

        Create execution for image type function, prepare_execution method
        raises exception.
        """
        function = self.create_function()
        function_id = function.id
        runtime_id = function.runtime_id
        db_api.update_function(
            function_id,
            {
                'code': {
                    'source': constants.IMAGE_FUNCTION,
                    'image': self.rand_name('image', prefix=self.prefix)
                }
            }
        )
        function = db_api.get_function(function_id)
        execution = self.create_execution(function_id=function_id)
        execution_id = execution.id
        prepare_execution = self.orchestrator.prepare_execution
        prepare_execution.side_effect = exc.OrchestratorException(
            'Exception in prepare_execution'
        )
        etcd_util_get_service_url_mock.return_value = None

        self.default_engine.create_execution(
            mock.Mock(), execution_id, function_id, 0, runtime_id)

        execution = db_api.get_execution(execution_id)

        self.assertEqual(status.ERROR, execution.status)
        self.assertEqual('', execution.logs)
        self.assertEqual({'output': 'Function execution failed.'},
                         execution.result)

    @mock.patch('qinling.utils.etcd_util.get_service_url')
    def test_create_execution_package_type_function(
        self,
        etcd_util_get_service_url_mock
    ):
        function = self.create_function()
        function_id = function.id
        runtime_id = function.runtime_id
        execution = self.create_execution(function_id=function_id)
        execution_id = execution.id
        self.default_engine.function_load_check = mock.Mock(return_value='')
        etcd_util_get_service_url_mock.return_value = None
        self.orchestrator.prepare_execution.return_value = (
            mock.Mock(), 'svc_url')
        self.orchestrator.run_execution.return_value = (
            True,
            {'success': True, 'logs': 'execution log',
             'output': 'success output'})

        self.default_engine.create_execution(
            mock.Mock(), execution_id, function_id, 0, runtime_id)

        self.default_engine.function_load_check.assert_called_once_with(
            function_id, 0, runtime_id)
        etcd_util_get_service_url_mock.assert_called_once_with(function_id, 0)
        self.orchestrator.prepare_execution.assert_called_once_with(
            function_id, 0, rlimit=self.rlimit, image=None,
            identifier=runtime_id, labels={'runtime_id': runtime_id},
            input=None)
        self.orchestrator.run_execution.assert_called_once_with(
            execution_id, function_id, 0, rlimit=self.rlimit, input=None,
            identifier=runtime_id, service_url='svc_url', entry=function.entry,
            trust_id=function.trust_id, timeout=function.timeout)

        execution = db_api.get_execution(execution_id)

        self.assertEqual(execution.status, status.SUCCESS)
        self.assertEqual(execution.logs, 'execution log')
        self.assertEqual(execution.result, {'output': 'success output'})

    def test_create_execution_loadcheck_exception(self):
        function = self.create_function()
        function_id = function.id
        runtime_id = function.runtime_id
        execution = self.create_execution(function_id=function_id)
        execution_id = execution.id
        self.default_engine.function_load_check = mock.Mock(
            side_effect=exc.OrchestratorException(
                'Exception in scaleup_function'
            )
        )

        self.default_engine.create_execution(
            mock.Mock(), execution_id, function_id, 0, runtime_id)

        execution = db_api.get_execution(execution_id)

        self.assertEqual(status.ERROR, execution.status)
        self.assertEqual('', execution.logs)
        self.assertEqual({'output': 'Function execution failed.'},
                         execution.result)

    @mock.patch('qinling.engine.utils.get_request_data')
    @mock.patch('qinling.engine.utils.url_request')
    @mock.patch('qinling.utils.etcd_util.get_service_url')
    def test_create_execution_found_service_url(
        self,
        etcd_util_get_service_url_mock,
        engine_utils_url_request_mock,
        engine_utils_get_request_data_mock
    ):
        function = self.create_function()
        function_id = function.id
        runtime_id = function.runtime_id
        execution = self.create_execution(function_id=function_id)
        execution_id = execution.id
        self.default_engine.function_load_check = mock.Mock(return_value='')
        etcd_util_get_service_url_mock.return_value = 'svc_url'
        engine_utils_get_request_data_mock.return_value = 'data'
        engine_utils_url_request_mock.return_value = (
            False,
            {'success': False, 'logs': 'execution log',
             'output': 'failed output'})

        self.default_engine.create_execution(
            mock.Mock(), execution_id, function_id, 0, runtime_id,
            input='input')

        self.default_engine.function_load_check.assert_called_once_with(
            function_id, 0, runtime_id)
        etcd_util_get_service_url_mock.assert_called_once_with(function_id, 0)
        engine_utils_get_request_data_mock.assert_called_once_with(
            mock.ANY, function_id, 0, execution_id, self.rlimit,
            'input', function.entry, function.trust_id,
            self.qinling_endpoint, function.timeout)
        engine_utils_url_request_mock.assert_called_once_with(
            self.default_engine.session, 'svc_url/execute', body='data')

        execution = db_api.get_execution(execution_id)

        self.assertEqual(execution.status, status.FAILED)
        self.assertEqual(execution.logs, 'execution log')
        self.assertEqual(execution.result,
                         {'success': False, 'output': 'failed output'})

    def test_delete_function(self):
        function_id = common.generate_unicode_uuid()

        self.default_engine.delete_function(mock.Mock(), function_id)

        self.orchestrator.delete_function.assert_called_once_with(
            function_id, 0
        )

    @mock.patch('qinling.utils.etcd_util.create_service_url')
    @mock.patch('qinling.utils.etcd_util.create_worker')
    def test_scaleup_function(
        self,
        etcd_util_create_worker_mock,
        etcd_util_create_service_url_mock
    ):
        function_id = common.generate_unicode_uuid()
        runtime_id = common.generate_unicode_uuid()
        self.orchestrator.scaleup_function.return_value = (['worker'], 'url')

        self.default_engine.scaleup_function(
            mock.Mock(), function_id, 0, runtime_id)

        self.orchestrator.scaleup_function.assert_called_once_with(
            function_id, 0, identifier=runtime_id, count=1)
        etcd_util_create_worker_mock.assert_called_once_with(
            function_id, 'worker', version=0)
        etcd_util_create_service_url_mock.assert_called_once_with(
            function_id, 'url', version=0)

    @mock.patch('qinling.utils.etcd_util.create_service_url')
    @mock.patch('qinling.utils.etcd_util.create_worker')
    def test_scaleup_function_multiple_workers(
        self,
        etcd_util_create_worker_mock,
        etcd_util_create_service_url_mock
    ):
        function_id = common.generate_unicode_uuid()
        runtime_id = common.generate_unicode_uuid()
        self.orchestrator.scaleup_function.return_value = (
            ['worker0', 'worker1'], 'url')

        self.default_engine.scaleup_function(
            mock.Mock(), function_id, 0, runtime_id, count=2
        )

        self.orchestrator.scaleup_function.assert_called_once_with(
            function_id, 0, identifier=runtime_id, count=2
        )
        # Two new workers are created.
        expected = [mock.call(function_id, 'worker0', version=0),
                    mock.call(function_id, 'worker1', version=0)]
        etcd_util_create_worker_mock.assert_has_calls(expected)
        etcd_util_create_service_url_mock.assert_called_once_with(
            function_id, 'url', version=0
        )

    @mock.patch('qinling.utils.etcd_util.delete_worker')
    @mock.patch('qinling.utils.etcd_util.get_workers')
    def test_scaledown_function(
        self, etcd_util_get_workers_mock, etcd_util_delete_workers_mock
    ):
        function_id = common.generate_unicode_uuid()
        etcd_util_get_workers_mock.return_value = [
            'worker_%d' % i for i in range(4)
        ]

        self.default_engine.scaledown_function(mock.Mock(), function_id)

        etcd_util_get_workers_mock.assert_called_once_with(
            function_id, 0)
        self.orchestrator.delete_worker.assert_called_once_with('worker_0')
        etcd_util_delete_workers_mock.assert_called_once_with(
            function_id, 'worker_0', version=0
        )

    @mock.patch('qinling.utils.etcd_util.delete_worker')
    @mock.patch('qinling.utils.etcd_util.get_workers')
    def test_scaledown_function_multiple_workers(
        self, etcd_util_get_workers_mock, etcd_util_delete_workers_mock
    ):
        function_id = common.generate_unicode_uuid()
        etcd_util_get_workers_mock.return_value = [
            'worker_%d' % i for i in range(4)
        ]

        self.default_engine.scaledown_function(mock.Mock(), function_id,
                                               count=2)

        etcd_util_get_workers_mock.assert_called_once_with(function_id, 0)
        # First two workers will be deleted.
        expected = [mock.call('worker_0'), mock.call('worker_1')]
        self.orchestrator.delete_worker.assert_has_calls(expected)
        self.assertEqual(2, self.orchestrator.delete_worker.call_count)
        expected = [
            mock.call(function_id, 'worker_0', version=0),
            mock.call(function_id, 'worker_1', version=0)
        ]
        etcd_util_delete_workers_mock.assert_has_calls(expected)
        self.assertEqual(2, etcd_util_delete_workers_mock.call_count)

    @mock.patch('qinling.utils.etcd_util.delete_worker')
    @mock.patch('qinling.utils.etcd_util.get_workers')
    def test_scaledown_function_leaving_one_worker(
        self, etcd_util_get_workers_mock, etcd_util_delete_workers_mock
    ):
        function_id = common.generate_unicode_uuid()
        etcd_util_get_workers_mock.return_value = [
            'worker_%d' % i for i in range(4)
        ]

        self.default_engine.scaledown_function(
            mock.Mock(), function_id, count=5)  # count > len(workers)

        etcd_util_get_workers_mock.assert_called_once_with(function_id, 0)
        # Only the first three workers will be deleted
        expected = [
            mock.call('worker_0'), mock.call('worker_1'), mock.call('worker_2')
        ]
        self.orchestrator.delete_worker.assert_has_calls(expected)
        self.assertEqual(3, self.orchestrator.delete_worker.call_count)
        expected = [
            mock.call(function_id, 'worker_0', version=0),
            mock.call(function_id, 'worker_1', version=0),
            mock.call(function_id, 'worker_2', version=0)
        ]
        etcd_util_delete_workers_mock.assert_has_calls(expected)
        self.assertEqual(3, etcd_util_delete_workers_mock.call_count)

    def test_get_runtime_pool(self):
        runtime = self.create_runtime()
        runtime_id = runtime.id

        self.default_engine.get_runtime_pool(mock.Mock(), runtime_id)

        self.orchestrator.get_pool.assert_called_once_with(runtime_id)
