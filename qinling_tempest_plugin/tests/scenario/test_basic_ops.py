# Copyright 2017 Catalyst IT Ltd
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

from tempest.lib.common.utils import data_utils
from tempest.lib import decorators

from qinling_tempest_plugin.tests import base


class BasicOpsTest(base.BaseQinlingTest):
    name_prefix = 'BasicOpsTest'
    create_runtime = False

    @decorators.idempotent_id('205fd749-2468-4d9f-9c05-45558d6d8f9e')
    def test_basic_ops(self):
        """Basic qinling operations test case, including following steps:

        1. Admin user creates a runtime.
        2. Normal user creates function.
        3. Normal user creates execution(invoke function).
        4. Check result and execution log.
        """
        name = data_utils.rand_name('runtime', prefix=self.name_prefix)
        resp, body = self.admin_client.create_runtime(self.image, name)
        self.assertEqual(201, resp.status)
        self.assertEqual(name, body['name'])

        # Wait for runtime to be available
        self.runtime_id = body['id']
        self.wait_runtime_available(self.runtime_id)
        self.addCleanup(self.admin_client.delete_resource, 'runtimes',
                        self.runtime_id, ignore_notfound=True)

        # Create function
        function_id = self.create_function()

        # Invoke function
        resp, body = self.client.create_execution(
            function_id, input='{"name": "Qinling"}'
        )
        # self.assertEqual(201, resp.status)
        # self.assertEqual('success', body['status'])
        execution_id = body['id']
        self.addCleanup(self.client.delete_resource, 'executions',
                        execution_id, ignore_notfound=True)

        # Get execution log
        resp, body = self.client.get_execution_log(execution_id)

        self.assertEqual(200, resp.status)
        self.assertIn('Hello, Qinling', body)
