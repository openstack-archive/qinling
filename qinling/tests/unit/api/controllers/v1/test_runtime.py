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
from qinling import status
from qinling.tests.unit.api import base
from qinling.tests.unit import base as test_base


class TestRuntimeController(base.APITest):
    def setUp(self):
        super(TestRuntimeController, self).setUp()

        # Insert a runtime record in db. The data will be removed in clean up.
        db_runtime = db_api.create_runtime(
            {
                'name': 'test_runtime',
                'image': 'python2.7',
                'project_id': test_base.DEFAULT_PROJECT_ID,
                'status': status.AVAILABLE
            }
        )
        self.runtime_id = db_runtime.id

    def test_get(self):
        resp = self.app.get('/v1/runtimes/%s' % self.runtime_id)

        expected = {
            'id': self.runtime_id,
            "image": "python2.7",
            "name": "test_runtime",
            "project_id": test_base.DEFAULT_PROJECT_ID,
            "status": status.AVAILABLE
        }

        self.assertEqual(200, resp.status_int)
        self._assertDictContainsSubset(resp.json, expected)
