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
import os

from tempest.lib import decorators
from tempest.lib import exceptions
import tenacity

from qinling_tempest_plugin.tests import base
from qinling_tempest_plugin.tests import utils


class FunctionsTest(base.BaseQinlingTest):
    name_prefix = 'FunctionsTest'

    def setUp(self):
        super(FunctionsTest, self).setUp()

        # Wait until runtime is available
        self.wait_runtime_available(self.runtime_id)
        self.python_zip_file = self.create_package()

    @decorators.idempotent_id('9c36ac64-9a44-4c44-9e44-241dcc6b0933')
    def test_crud_function(self):
        # Create function
        md5sum = utils.md5(self.python_zip_file)
        function_id = self.create_function(self.python_zip_file, md5sum=md5sum)

        # Get functions
        resp, body = self.client.get_resources('functions')
        self.assertEqual(200, resp.status)
        self.assertIn(
            function_id,
            [function['id'] for function in body['functions']]
        )

        # Download function package
        resp, data = self.client.download_function(function_id)
        self.assertEqual(200, resp.status)
        self.assertEqual('application/zip', resp['content-type'])
        self.assertEqual(os.path.getsize(self.python_zip_file), len(data))

        # Delete function
        resp = self.client.delete_resource('functions', function_id)
        self.assertEqual(204, resp.status)

    @decorators.idempotent_id('1fec41cd-b753-4cad-90c5-c89d7e710317')
    def test_create_function_md5mismatch(self):
        fake_md5 = "e807f1fcf82d132f9bb018ca6738a19f"

        with open(self.python_zip_file, 'rb') as package_data:
            resp, body = self.client.create_function(
                {"source": "package", "md5sum": fake_md5},
                self.runtime_id,
                name='test_create_function_md5mismatch',
                package_data=package_data
            )

        self.assertEqual(400, resp.status_code)

    @decorators.idempotent_id('f8dde7fc-fbcc-495c-9b39-70666b7d3f64')
    def test_get_by_admin(self):
        """test_get_by_admin

        Admin user can get the function by directly specifying the function id.
        """
        function_id = self.create_function(self.python_zip_file)

        resp, body = self.admin_client.get_function(function_id)

        self.assertEqual(200, resp.status)
        self.assertEqual(function_id, body['id'])

    @decorators.idempotent_id('051f3106-df01-4fcd-a0a3-c81c99653163')
    def test_get_all_admin(self):
        """test_get_all_admin

        Admin user needs to specify filters to get all the functions.
        """
        function_id = self.create_function(self.python_zip_file)

        resp, body = self.admin_client.get_resources('functions')

        self.assertEqual(200, resp.status)
        self.assertNotIn(
            function_id,
            [function['id'] for function in body['functions']]
        )

        resp, body = self.admin_client.get_resources(
            'functions?all_projects=true'
        )

        self.assertEqual(200, resp.status)
        self.assertIn(
            function_id,
            [function['id'] for function in body['functions']]
        )

    @decorators.idempotent_id('cd396bda-2174-4335-9f7f-2457aab61a4a')
    def test_get_all_not_allowed(self):
        # Get other projects functions by normal user
        context = self.assertRaises(
            exceptions.Forbidden,
            self.client.get_resources,
            'functions?all_projects=true'
        )
        self.assertIn(
            'Operation not allowed',
            context.resp_body.get('faultstring')
        )

    @decorators.idempotent_id('5cb44ee4-6c0c-4ede-9e6c-e1b9109eaa2c')
    def test_delete_not_allowed(self):
        """Even admin user can not delete other project's function."""
        function_id = self.create_function(self.python_zip_file)

        self.assertRaises(
            exceptions.Forbidden,
            self.admin_client.delete_resource,
            'functions',
            function_id
        )

    @decorators.idempotent_id('45df227e-3399-4412-a8d3-d40c1290bc1c')
    def test_detach(self):
        """Admin only operation."""
        function_id = self.create_function(self.python_zip_file)
        resp, _ = self.client.create_execution(
            function_id, input='{"name": "Qinling"}'
        )
        self.assertEqual(201, resp.status)

        resp, body = self.admin_client.get_function_workers(function_id)
        self.assertEqual(200, resp.status)
        self.assertEqual(1, len(body['workers']))

        # Detach function
        resp, _ = self.admin_client.detach_function(function_id)
        self.assertEqual(202, resp.status)

        def _assert_workers():
            resp, body = self.admin_client.get_function_workers(function_id)
            self.assertEqual(200, resp.status)
            self.assertEqual(0, len(body['workers']))

        r = tenacity.Retrying(
            wait=tenacity.wait_fixed(1),
            stop=tenacity.stop_after_attempt(5),
            retry=tenacity.retry_if_exception_type(AssertionError)
        )
        r.call(_assert_workers)
