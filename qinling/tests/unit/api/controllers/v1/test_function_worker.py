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

from unittest import mock

from oslo_utils import uuidutils
from qinling.tests.unit.api import base


class TestFunctionWorkerController(base.APITest):
    @mock.patch('qinling.utils.etcd_util.get_workers')
    def test_get_all_workers(self, mock_get_workers):
        function_id = uuidutils.generate_uuid()
        mock_get_workers.return_value = ['test_worker0', 'test_worker1']

        resp = self.app.get('/v1/functions/%s/workers' % function_id)
        self.assertEqual(200, resp.status_int)
        self._assert_multiple_items(
            resp.json['workers'], 2, function_id=function_id
        )
        self._assert_single_item(
            resp.json['workers'], worker_name='test_worker0'
        )
        self._assert_single_item(
            resp.json['workers'], worker_name='test_worker1'
        )

    @mock.patch('qinling.utils.etcd_util.get_workers')
    def test_get_all_version_workers(self, mock_get_workers):
        function_id = uuidutils.generate_uuid()
        mock_get_workers.return_value = ['test_worker0', 'test_worker1']

        resp = self.app.get(
            '/v1/functions/%s/workers?function_version=1' % function_id
        )

        self.assertEqual(200, resp.status_int)
        mock_get_workers.assert_called_once_with(function_id, version=1)
        self._assert_multiple_items(
            resp.json['workers'],
            2,
            function_id=function_id,
            function_version=1
        )
        self._assert_single_item(
            resp.json['workers'], worker_name='test_worker0'
        )
        self._assert_single_item(
            resp.json['workers'], worker_name='test_worker1'
        )

    def test_get_all_version_workers_not_int(self):
        function_id = uuidutils.generate_uuid()
        resp = self.app.get(
            '/v1/functions/%s/workers?function_version=invalid' % function_id,
            expect_errors=True
        )

        self.assertEqual(400, resp.status_int)
