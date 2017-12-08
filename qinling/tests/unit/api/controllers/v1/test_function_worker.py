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

from qinling.db import api as db_api
from qinling.tests.unit.api import base

TEST_CASE_NAME = 'TestFunctionWorkerController'


class TestFunctionWorkerController(base.APITest):
    def setUp(self):
        super(TestFunctionWorkerController, self).setUp()

        db_func = self.create_function(prefix=TEST_CASE_NAME)
        self.function_id = db_func.id

    def test_get_all_workers(self):
        db_worker = db_api.create_function_worker(
            {
                'function_id': self.function_id,
                'worker_name': 'worker_1',
            }
        )
        expected = {
            "id": db_worker.id,
            "function_id": self.function_id,
            "worker_name": "worker_1",
        }

        resp = self.app.get('/v1/functions/%s/workers' % self.function_id)

        self.assertEqual(200, resp.status_int)
        actual = self._assert_single_item(
            resp.json['workers'], id=db_worker.id
        )
        self._assertDictContainsSubset(actual, expected)
