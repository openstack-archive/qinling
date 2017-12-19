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
import time

import mock
from oslo_config import cfg

from qinling.db import api as db_api
from qinling.engine import default_engine
from qinling.services import periodics
from qinling.tests.unit import base

CONF = cfg.CONF


class TestPeriodics(base.DbTestCase):
    TEST_CASE_NAME = 'TestPeriodics'

    @mock.patch('qinling.utils.etcd_util.delete_function')
    @mock.patch('qinling.utils.etcd_util.get_service_url')
    def test_function_service_expiration(self, mock_etcd_url,
                                         mock_etcd_delete):
        db_func = self.create_function(
            runtime_id=None, prefix=self.TEST_CASE_NAME
        )
        function_id = db_func.id
        # Update function to simulate function execution
        db_api.update_function(function_id, {'count': 1})
        time.sleep(1.5)

        mock_k8s = mock.Mock()
        mock_etcd_url.return_value = 'http://localhost:37718'
        self.override_config('function_service_expiration', 1, 'engine')
        engine = default_engine.DefaultEngine(mock_k8s)
        periodics.handle_function_service_expiration(self.ctx, engine)

        self.assertEqual(1, mock_k8s.delete_function.call_count)
        args, kwargs = mock_k8s.delete_function.call_args
        self.assertIn(function_id, args)
        mock_etcd_delete.assert_called_once_with(function_id)
