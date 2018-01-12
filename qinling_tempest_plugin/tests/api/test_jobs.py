# Copyright 2018 Catalyst IT Ltd
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
from tempest.lib import decorators

from qinling_tempest_plugin.tests import base


class JobsTest(base.BaseQinlingTest):
    name_prefix = 'JobsTest'

    def setUp(self):
        super(JobsTest, self).setUp()

        self.await_runtime_available(self.runtime_id)
        self.function_id = self.create_function()

    @decorators.idempotent_id('68e4d562-f762-11e7-875d-00224d6b7bc1')
    def test_get_all_admin(self):
        """Admin user can get jobs of other projects"""
        job_id = self.create_job(self.function_id)

        resp, body = self.admin_client.get_resources(
            'jobs?all_projects=true'
        )
        self.assertEqual(200, resp.status)
        self.assertIn(
            job_id,
            [item['id'] for item in body['jobs']]
        )
