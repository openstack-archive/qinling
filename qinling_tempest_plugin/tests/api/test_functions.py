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
import pkg_resources
import tempfile
import zipfile

from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions
import tenacity

from qinling_tempest_plugin.tests import base


class FunctionsTest(base.BaseQinlingTest):
    name_prefix = 'FunctionsTest'

    @classmethod
    def resource_setup(cls):
        super(FunctionsTest, cls).resource_setup()

        cls.runtime_id = None

        # Create runtime for function tests
        name = data_utils.rand_name('runtime', prefix=cls.name_prefix)
        _, body = cls.admin_client.create_runtime(
            'openstackqinling/python-runtime', name
        )
        cls.runtime_id = body['id']

    @classmethod
    def resource_cleanup(cls):
        if cls.runtime_id:
            cls.admin_client.delete_resource('runtimes', cls.runtime_id)

        super(FunctionsTest, cls).resource_cleanup()

    def setUp(self):
        super(FunctionsTest, self).setUp()

        # Wait until runtime is available
        self.await_runtime_available(self.runtime_id)

        python_file_path = pkg_resources.resource_filename(
            'qinling_tempest_plugin',
            "functions/python_test.py"
        )
        base_name, extention = os.path.splitext(python_file_path)
        module_name = os.path.basename(base_name)
        self.python_zip_file = os.path.join(
            tempfile.gettempdir(),
            '%s.zip' % module_name
        )

        if not os.path.isfile(self.python_zip_file):
            zf = zipfile.ZipFile(self.python_zip_file, mode='w')
            try:
                # Use default compression mode, may change in future.
                zf.write(
                    python_file_path,
                    '%s%s' % (module_name, extention),
                    compress_type=zipfile.ZIP_STORED
                )
            finally:
                zf.close()

    @decorators.idempotent_id('9c36ac64-9a44-4c44-9e44-241dcc6b0933')
    def test_crud_function(self):
        # Create function
        function_id = self.create_function(self.python_zip_file)

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
        self.assertEqual(os.path.getsize(self.python_zip_file), len(data))

        # Delete function
        resp = self.client.delete_resource('functions', function_id)
        self.assertEqual(204, resp.status)

    @decorators.idempotent_id('051f3106-df01-4fcd-a0a3-c81c99653163')
    def test_get_all_admin(self):
        # Create function by normal user
        function_id = self.create_function(self.python_zip_file)

        # Get functions by admin
        resp, body = self.admin_client.get_resources('functions')

        self.assertEqual(200, resp.status)
        self.assertNotIn(
            function_id,
            [function['id'] for function in body['functions']]
        )

        # Get other projects functions by admin
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
        resp, _ = self.client.create_execution(function_id,
                                               input={'name': 'Qinling'})
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
