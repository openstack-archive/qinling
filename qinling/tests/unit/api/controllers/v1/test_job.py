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
from datetime import timedelta

from qinling.tests.unit.api import base


class TestJobController(base.APITest):
    def setUp(self):
        super(TestJobController, self).setUp()

        # Insert a function record in db for each test case. The data will be
        # removed automatically in db clean up.
        db_function = self.create_function(prefix='TestJobController')
        self.function_id = db_function.id

    def test_post(self):
        body = {
            'name': self.rand_name('job', prefix='TestJobController'),
            'first_execution_time': str(
                datetime.utcnow() + timedelta(hours=1)),
            'function_id': self.function_id
        }
        resp = self.app.post_json('/v1/jobs', body)

        self.assertEqual(201, resp.status_int)

    def test_delete(self):
        job_id = self.create_job(
            self.function_id, prefix='TestJobController'
        ).id

        resp = self.app.delete('/v1/jobs/%s' % job_id)

        self.assertEqual(204, resp.status_int)
