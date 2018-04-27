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
from tempest.lib import exceptions

from qinling_tempest_plugin.tests import base


class FunctionVersionsTest(base.BaseQinlingTest):
    name_prefix = 'FunctionVersionsTest'

    def setUp(self):
        super(FunctionVersionsTest, self).setUp()

        # Wait until runtime is available
        self.await_runtime_available(self.runtime_id)

    @decorators.idempotent_id('ce630c59-a79d-4b2d-89af-c7c5c8f8bd3f')
    def test_create(self):
        function_id = self.create_function()
        new_version = self.create_function_version(function_id)

        self.assertEqual(1, new_version)

        resp, body = self.client.get_resources(
            'functions/%s/versions' % function_id)

        self.assertEqual(200, resp.status)
        self.assertIn(
            new_version,
            [v['version_number'] for v in body['function_versions']]
        )

    @decorators.idempotent_id('9da2d24c-2ce4-4e6f-9e44-74ef1b9ec3cc')
    def test_create_function_no_change(self):
        function_id = self.create_function()
        self.create_function_version(function_id)

        self.assertRaises(
            exceptions.Forbidden,
            self.client.create_function_version,
            function_id
        )

    @decorators.idempotent_id('6864d134-fbb9-4738-9721-b541c4362789')
    def test_create_function_change(self):
        function_id = self.create_function()
        version_1 = self.create_function_version(function_id)
        self.update_function_package(function_id,
                                     "python/test_python_sleep.py")
        version_2 = self.create_function_version(function_id)

        self.assertGreater(version_2, version_1)

        resp, body = self.client.get_resources(
            'functions/%s/versions' % function_id)
        self.assertEqual(200, resp.status)

        numbers = [v['version_number'] for v in body['function_versions']]
        self.assertIn(version_1, numbers)
        self.assertIn(version_2, numbers)
