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

import mock

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
            self.orchestrator, self.qinling_endpoint)

    def _create_running_executions(self, function_id, num):
        for _i in range(num):
            self.create_execution(function_id=function_id,
                                  prefix='TestDefaultEngine')

    def test_create_runtime(self):
        runtime = self.create_runtime(prefix='TestDefaultEngine')
        runtime_id = runtime.id
        # Set status to verify it is changed during creation.
        db_api.update_runtime(runtime_id, {'status': status.CREATING})

        self.default_engine.create_runtime(mock.Mock(), runtime_id)

        self.orchestrator.create_pool.assert_called_once_with(
            runtime_id, runtime.image)
        runtime = db_api.get_runtime(runtime_id)
        self.assertEqual(status.AVAILABLE, runtime.status)

    def test_create_runtime_failed(self):
        runtime = self.create_runtime(prefix='TestDefaultEngine')
        runtime_id = runtime.id
        # Set status to verify it is changed during creation.
        db_api.update_runtime(runtime_id, {'status': status.CREATING})
        self.orchestrator.create_pool.side_effect = RuntimeError

        self.default_engine.create_runtime(mock.Mock(), runtime_id)

        self.orchestrator.create_pool.assert_called_once_with(
            runtime_id, runtime.image)
        runtime = db_api.get_runtime(runtime_id)
        self.assertEqual(status.ERROR, runtime.status)

    def test_delete_runtime(self):
        runtime = self.create_runtime(prefix='TestDefaultEngine')
        runtime_id = runtime.id

        self.default_engine.delete_runtime(mock.Mock(), runtime_id)

        self.orchestrator.delete_pool.assert_called_once_with(
            runtime_id)
        self.assertRaisesRegexp(
            exc.DBEntityNotFoundError,
            "^Runtime not found \[id=%s\]$" % runtime_id,
            db_api.get_runtime, runtime_id)

    def test_update_runtime(self):
        runtime = self.create_runtime(prefix='TestDefaultEngine')
        runtime_id = runtime.id
        # Set status to verify it is changed during update.
        db_api.update_runtime(runtime_id, {'status': status.UPGRADING})
        image = self.rand_name('new_image', prefix='TestDefaultEngine')
        pre_image = self.rand_name('pre_image', prefix='TestDefaultEngine')
        self.orchestrator.update_pool.return_value = True

        self.default_engine.update_runtime(
            mock.Mock(), runtime_id, image, pre_image)

        self.orchestrator.update_pool.assert_called_once_with(
            runtime_id, image=image)
        runtime = db_api.get_runtime(runtime_id)
        self.assertEqual(runtime.status, status.AVAILABLE)

    def test_update_runtime_rollbacked(self):
        runtime = self.create_runtime(prefix='TestDefaultEngine')
        runtime_id = runtime.id
        # Set status to verify it is changed during update.
        db_api.update_runtime(runtime_id, {'status': status.UPGRADING})
        image = self.rand_name('new_image', prefix='TestDefaultEngine')
        pre_image = self.rand_name('pre_image', prefix='TestDefaultEngine')
        self.orchestrator.update_pool.return_value = False

        self.default_engine.update_runtime(
            mock.Mock(), runtime_id, image, pre_image)

        self.orchestrator.update_pool.assert_called_once_with(
            runtime_id, image=image)
        runtime = db_api.get_runtime(runtime_id)
        self.assertEqual(runtime.image, pre_image)
        self.assertEqual(runtime.status, status.AVAILABLE)

    @mock.patch('qinling.utils.etcd_util.get_workers')
    @mock.patch('qinling.utils.etcd_util.get_worker_lock')
    def test_function_load_check_no_worker_scaleup(
        self,
        etcd_util_get_worker_lock_mock,
        etcd_util_get_workers_mock
    ):
        function_id = common.generate_unicode_uuid()
        runtime_id = common.generate_unicode_uuid()
        lock = mock.Mock()
        (
            etcd_util_get_worker_lock_mock.return_value.__enter__.return_value
        ) = lock
        lock.is_acquired.return_value = True
        etcd_util_get_workers_mock.return_value = []  # len(workers) = 0
        self.default_engine.scaleup_function = mock.Mock()

        self.default_engine.function_load_check(function_id, runtime_id)

        etcd_util_get_workers_mock.assert_called_once_with(function_id)
        self.default_engine.scaleup_function.assert_called_once_with(
            None, function_id, runtime_id, 1)

    @mock.patch('qinling.utils.etcd_util.get_workers')
    @mock.patch('qinling.utils.etcd_util.get_worker_lock')
    def test_function_load_check_concurrency_scaleup(
        self,
        etcd_util_get_worker_lock_mock,
        etcd_util_get_workers_mock
    ):
        function = self.create_function(prefix='TestDefaultEngine')
        function_id = function.id
        runtime_id = function.runtime_id
        lock = mock.Mock()
        (
            etcd_util_get_worker_lock_mock.return_value.__enter__.return_value
        ) = lock
        lock.is_acquired.return_value = True
        # The default concurrency is 3, we use 4 running executions against
        # 1 worker so that there will be a scaling up.
        etcd_util_get_workers_mock.return_value = range(1)
        self._create_running_executions(function_id, 4)
        self.default_engine.scaleup_function = mock.Mock()

        self.default_engine.function_load_check(function_id, runtime_id)

        etcd_util_get_workers_mock.assert_called_once_with(function_id)
        self.default_engine.scaleup_function.assert_called_once_with(
            None, function_id, runtime_id, 1)

    @mock.patch('qinling.utils.etcd_util.get_workers')
    @mock.patch('qinling.utils.etcd_util.get_worker_lock')
    def test_function_load_check_not_scaleup(
        self,
        etcd_util_get_worker_lock_mock,
        etcd_util_get_workers_mock
    ):
        function = self.create_function(prefix='TestDefaultEngine')
        function_id = function.id
        runtime_id = function.runtime_id
        lock = mock.Mock()
        (
            etcd_util_get_worker_lock_mock.return_value.__enter__.return_value
        ) = lock
        lock.is_acquired.return_value = True
        # The default concurrency is 3, we use 3 running executions against
        # 1 worker so that there won't be a scaling up.
        etcd_util_get_workers_mock.return_value = range(1)
        self._create_running_executions(function_id, 3)
        self.default_engine.scaleup_function = mock.Mock()

        self.default_engine.function_load_check(function_id, runtime_id)

        etcd_util_get_workers_mock.assert_called_once_with(function_id)
        self.default_engine.scaleup_function.assert_not_called()

    @mock.patch('qinling.utils.etcd_util.get_workers')
    @mock.patch('qinling.utils.etcd_util.get_worker_lock')
    def test_function_load_check_lock_wait(
        self,
        etcd_util_get_worker_lock_mock,
        etcd_util_get_workers_mock
    ):
        function = self.create_function(prefix='TestDefaultEngine')
        function_id = function.id
        runtime_id = function.runtime_id
        lock = mock.Mock()
        (
            etcd_util_get_worker_lock_mock.return_value.__enter__.return_value
        ) = lock
        # Lock is acquired upon the third try.
        lock.is_acquired.side_effect = [False, False, True]
        etcd_util_get_workers_mock.return_value = range(1)
        self._create_running_executions(function_id, 3)
        self.default_engine.scaleup_function = mock.Mock()

        self.default_engine.function_load_check(function_id, runtime_id)

        self.assertEqual(3, lock.is_acquired.call_count)
        etcd_util_get_workers_mock.assert_called_once_with(function_id)
        self.default_engine.scaleup_function.assert_not_called()

    @mock.patch('qinling.utils.etcd_util.get_service_url')
    def test_create_execution(
            self,
            etcd_util_get_service_url_mock
    ):
        function = self.create_function(prefix='TestDefaultEngine')
        function_id = function.id
        runtime_id = function.runtime_id
        db_api.update_function(
            function_id,
            {
                'code': {
                    'source': constants.IMAGE_FUNCTION,
                    'image': self.rand_name('image',
                                            prefix='TestDefaultEngine')
                }
            }
        )
        function = db_api.get_function(function_id)
        execution_1 = self.create_execution(
            function_id=function_id, prefix='TestDefaultEngine')
        execution_1_id = execution_1.id
        execution_2 = self.create_execution(
            function_id=function_id, prefix='TestDefaultEngine')
        execution_2_id = execution_2.id
        self.default_engine.function_load_check = mock.Mock()
        etcd_util_get_service_url_mock.return_value = None
        self.orchestrator.prepare_execution.return_value = (
            mock.Mock(), None)
        self.orchestrator.run_execution.side_effect = [
            (True, 'success result'),
            (False, 'failed result')]

        # Try create two executions, with different results
        self.default_engine.create_execution(
            mock.Mock(), execution_1_id, function_id, runtime_id)
        self.default_engine.create_execution(
            mock.Mock(), execution_2_id, function_id, runtime_id,
            input='input')

        self.default_engine.function_load_check.assert_not_called()
        get_service_url_calls = [
            mock.call(function_id), mock.call(function_id)]
        etcd_util_get_service_url_mock.assert_has_calls(get_service_url_calls)
        self.assertEqual(2, etcd_util_get_service_url_mock.call_count)
        prepare_calls = [
            mock.call(function_id,
                      image=function.code['image'],
                      identifier=mock.ANY,
                      labels=None,
                      input=None),
            mock.call(function_id,
                      image=function.code['image'],
                      identifier=mock.ANY,
                      labels=None,
                      input='input')]
        self.orchestrator.prepare_execution.assert_has_calls(prepare_calls)
        self.assertEqual(2, self.orchestrator.prepare_execution.call_count)
        run_calls = [
            mock.call(execution_1_id,
                      function_id,
                      input=None,
                      identifier=mock.ANY,
                      service_url=None,
                      entry=function.entry,
                      trust_id=function.trust_id),
            mock.call(execution_2_id,
                      function_id,
                      input='input',
                      identifier=mock.ANY,
                      service_url=None,
                      entry=function.entry,
                      trust_id=function.trust_id)]
        self.orchestrator.run_execution.assert_has_calls(run_calls)
        self.assertEqual(2, self.orchestrator.run_execution.call_count)
        execution_1 = db_api.get_execution(execution_1_id)
        execution_2 = db_api.get_execution(execution_2_id)
        self.assertEqual(execution_1.status, status.SUCCESS)
        self.assertEqual(execution_1.logs, '')
        self.assertEqual(execution_1.result, {'output': 'success result'})
        self.assertEqual(execution_2.status, status.FAILED)
        self.assertEqual(execution_2.logs, '')
        self.assertEqual(execution_2.result, {'output': 'failed result'})

    @mock.patch('qinling.utils.etcd_util.get_service_url')
    def test_create_execution_prepare_execution_exception(
            self,
            etcd_util_get_service_url_mock
    ):
        function = self.create_function(prefix='TestDefaultEngine')
        function_id = function.id
        runtime_id = function.runtime_id
        db_api.update_function(
            function_id,
            {
                'code': {
                    'source': constants.IMAGE_FUNCTION,
                    'image': self.rand_name('image',
                                            prefix='TestDefaultEngine')
                }
            }
        )
        function = db_api.get_function(function_id)
        execution = self.create_execution(
            function_id=function_id, prefix='TestDefaultEngine')
        execution_id = execution.id
        prepare_execution = self.orchestrator.prepare_execution
        prepare_execution.side_effect = exc.OrchestratorException(
            'Exception in prepare_execution'
        )
        etcd_util_get_service_url_mock.return_value = None

        self.default_engine.create_execution(
            mock.Mock(), execution_id, function_id, runtime_id)

        execution = db_api.get_execution(execution_id)
        self.assertEqual(execution.status, status.ERROR)
        self.assertEqual(execution.logs, '')
        self.assertEqual(execution.result, {})

    @mock.patch('qinling.utils.etcd_util.get_service_url')
    def test_create_execution_not_image_source(
            self,
            etcd_util_get_service_url_mock
    ):
        function = self.create_function(prefix='TestDefaultEngine')
        function_id = function.id
        runtime_id = function.runtime_id
        execution = self.create_execution(
            function_id=function_id, prefix='TestDefaultEngine')
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
            mock.Mock(), execution_id, function_id, runtime_id)

        self.default_engine.function_load_check.assert_called_once_with(
            function_id, runtime_id)
        etcd_util_get_service_url_mock.assert_called_once_with(function_id)
        self.orchestrator.prepare_execution.assert_called_once_with(
            function_id, image=None, identifier=runtime_id,
            labels={'runtime_id': runtime_id}, input=None)
        self.orchestrator.run_execution.assert_called_once_with(
            execution_id, function_id, input=None, identifier=runtime_id,
            service_url='svc_url', entry=function.entry,
            trust_id=function.trust_id)
        execution = db_api.get_execution(execution_id)
        self.assertEqual(execution.status, status.SUCCESS)
        self.assertEqual(execution.logs, 'execution log')
        self.assertEqual(execution.result, {'output': 'success output'})

    def test_create_execution_not_image_source_scaleup_exception(self):
        function = self.create_function(prefix='TestDefaultEngine')
        function_id = function.id
        runtime_id = function.runtime_id
        execution = self.create_execution(
            function_id=function_id, prefix='TestDefaultEngine')
        execution_id = execution.id
        self.default_engine.function_load_check = mock.Mock(
            side_effect=exc.OrchestratorException(
                'Exception in scaleup_function'
            )
        )

        self.default_engine.create_execution(
            mock.Mock(), execution_id, function_id, runtime_id)

        execution = db_api.get_execution(execution_id)
        self.assertEqual(execution.status, status.ERROR)
        self.assertEqual(execution.logs, '')
        self.assertEqual(execution.result, {})

    @mock.patch('qinling.engine.utils.get_request_data')
    @mock.patch('qinling.engine.utils.url_request')
    @mock.patch('qinling.utils.etcd_util.get_service_url')
    def test_create_execution_found_service_url(
            self,
            etcd_util_get_service_url_mock,
            engine_utils_url_request_mock,
            engine_utils_get_request_data_mock
    ):
        function = self.create_function(prefix='TestDefaultEngine')
        function_id = function.id
        runtime_id = function.runtime_id
        execution = self.create_execution(
            function_id=function_id, prefix='TestDefaultEngine')
        execution_id = execution.id
        self.default_engine.function_load_check = mock.Mock(return_value='')
        etcd_util_get_service_url_mock.return_value = 'svc_url'
        engine_utils_get_request_data_mock.return_value = 'data'
        engine_utils_url_request_mock.return_value = (
            False,
            {'success': False, 'logs': 'execution log',
             'output': 'failed output'})

        self.default_engine.create_execution(
            mock.Mock(), execution_id, function_id, runtime_id, input='input')

        self.default_engine.function_load_check.assert_called_once_with(
            function_id, runtime_id)
        etcd_util_get_service_url_mock.assert_called_once_with(function_id)
        engine_utils_get_request_data_mock.assert_called_once_with(
            mock.ANY, function_id, execution_id,
            'input', function.entry, function.trust_id,
            self.qinling_endpoint)
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
            function_id)

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
            mock.Mock(), function_id, runtime_id)

        self.orchestrator.scaleup_function.assert_called_once_with(
            function_id, identifier=runtime_id, count=1)
        etcd_util_create_worker_mock.assert_called_once_with(
            function_id, 'worker')
        etcd_util_create_service_url_mock.assert_called_once_with(
            function_id, 'url')

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
            mock.Mock(), function_id, runtime_id, count=2)

        self.orchestrator.scaleup_function.assert_called_once_with(
            function_id, identifier=runtime_id, count=2)
        # Two new workers are created.
        expected = [mock.call(function_id, 'worker0'),
                    mock.call(function_id, 'worker1')]
        etcd_util_create_worker_mock.assert_has_calls(expected)
        self.assertEqual(2, etcd_util_create_worker_mock.call_count)
        etcd_util_create_service_url_mock.assert_called_once_with(
            function_id, 'url')

    @mock.patch('qinling.utils.etcd_util.get_workers')
    def test_scaledown_function(self, etcd_util_get_workers_mock):
        function_id = common.generate_unicode_uuid()
        etcd_util_get_workers_mock.return_value = range(4)

        self.default_engine.scaledown_function(mock.Mock(), function_id)

        etcd_util_get_workers_mock.assert_called_once_with(
            function_id)
        self.orchestrator.delete_worker.assert_called_once_with(0)

    @mock.patch('qinling.utils.etcd_util.get_workers')
    def test_scaledown_function_multiple_workers(
            self, etcd_util_get_workers_mock
    ):
        function_id = common.generate_unicode_uuid()
        etcd_util_get_workers_mock.return_value = range(4)

        self.default_engine.scaledown_function(
            mock.Mock(), function_id, count=2)

        etcd_util_get_workers_mock.assert_called_once_with(
            function_id)
        # First two workers will be deleted.
        expected = [mock.call(0), mock.call(1)]
        self.orchestrator.delete_worker.assert_has_calls(expected)
        self.assertEqual(2, self.orchestrator.delete_worker.call_count)

    @mock.patch('qinling.utils.etcd_util.get_workers')
    def test_scaledown_function_leaving_one_worker(
            self, etcd_util_get_workers_mock
    ):
        function_id = common.generate_unicode_uuid()
        etcd_util_get_workers_mock.return_value = range(4)

        self.default_engine.scaledown_function(
            mock.Mock(), function_id, count=5)  # count > len(workers)

        etcd_util_get_workers_mock.assert_called_once_with(
            function_id)
        # Only the first three workers will be deleted
        expected = [mock.call(0), mock.call(1), mock.call(2)]
        self.orchestrator.delete_worker.assert_has_calls(expected)
        self.assertEqual(3, self.orchestrator.delete_worker.call_count)
