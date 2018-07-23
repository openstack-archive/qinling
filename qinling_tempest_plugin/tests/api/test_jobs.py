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
from datetime import datetime
from datetime import timedelta

from tempest.lib import decorators

from qinling_tempest_plugin.tests import base


class JobsTest(base.BaseQinlingTest):
    name_prefix = 'JobsTest'

    def setUp(self):
        super(JobsTest, self).setUp()

        self.wait_runtime_available(self.runtime_id)
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

    @decorators.idempotent_id('82a694a7-d3b5-4b6c-86e5-5fac6eae0f2a')
    def test_create_with_function_version(self):
        version = self.create_function_version(self.function_id)
        # first_execution_time is at least 1 min ahead of current time.
        first_execution_time = str(datetime.utcnow() + timedelta(seconds=90))
        job_id = self.create_job(self.function_id, version=version,
                                 first_execution_time=first_execution_time)

        # Wait for job to be finished
        self.wait_job_done(job_id)

        resp, body = self.client.get_resources(
            'executions',
            {'description': 'has:%s' % job_id}
        )
        self.assertEqual(200, resp.status)
        self.assertEqual(1, len(body['executions']))

        exec_id = body['executions'][0]['id']
        self.wait_execution_success(exec_id)

        resp, body = self.client.get_execution_log(exec_id)
        self.assertEqual(200, resp.status)
        self.assertIn('Hello, World', body)

    @decorators.idempotent_id('2ff6b90b-0432-44ec-8698-eed1c7fb7f04')
    def test_create_with_function_alias(self):
        version = self.create_function_version(self.function_id)
        function_alias = self.create_function_alias(self.function_id, version)
        # first_execution_time is at least 1 min ahead of current time.
        first_execution_time = str(datetime.utcnow() + timedelta(seconds=90))
        job_id = self.create_job(function_alias=function_alias,
                                 first_execution_time=first_execution_time)

        # Wait for job to be finished
        self.wait_job_done(job_id)

        resp, body = self.client.get_resources(
            'executions',
            {'description': 'has:%s' % job_id}
        )
        self.assertEqual(200, resp.status)
        self.assertEqual(1, len(body['executions']))

        exec_id = body['executions'][0]['id']
        self.wait_execution_success(exec_id)

        resp, body = self.client.get_execution_log(exec_id)
        self.assertEqual(200, resp.status)
        self.assertIn('Hello, World', body)
