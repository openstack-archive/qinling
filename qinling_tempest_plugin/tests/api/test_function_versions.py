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
import tenacity

from qinling_tempest_plugin.tests import base


class FunctionVersionsTest(base.BaseQinlingTest):
    name_prefix = 'FunctionVersionsTest'

    def setUp(self):
        super(FunctionVersionsTest, self).setUp()

        # Wait until runtime is available
        self.wait_runtime_available(self.runtime_id)

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

    @decorators.idempotent_id('3f735ed4-64b0-4ec3-8bf2-507e38dcea19')
    def test_create_admin_not_allowed(self):
        """test_create_admin_not_allowed

        Even admin user can not create function version for normal user's
        function.
        """
        function_id = self.create_function()

        self.assertRaises(
            exceptions.NotFound,
            self.admin_client.create_function_version,
            function_id
        )

    # @decorators.idempotent_id('78dc5552-fcb8-4b27-86f7-5f3d96143934')
    # def test_create_version_lock_failed(self):
    #     """test_create_version_lock_failed
    #
    #     Creating a function requires a lock. If qinling failed to acquire the
    #     lock then an error would be returned after some retries.
    #
    #     In this test we acquire the lock manually, so that qinling will fail
    #     to acquire the lock.
    #     """
    #     function_id = self.create_function()
    #
    #     from qinling_tempest_plugin.tests import utils
    #     etcd3_client = utils.get_etcd_client()
    #     lock_id = "function_version_%s" % function_id
    #     with etcd3_client.lock(id=lock_id):
    #         self.assertRaises(
    #             exceptions.ServerFault,
    #             self.client.create_function_version,
    #             function_id
    #         )

    @decorators.idempotent_id('43c06f41-d116-43a7-a61c-115f7591b22e')
    def test_get_by_admin(self):
        """Admin user can get normal user's function version."""
        function_id = self.create_function()
        version = self.create_function_version(function_id)

        resp, body = self.admin_client.get_function_version(function_id,
                                                            version)

        self.assertEqual(200, resp.status)
        self.assertEqual(version, body.get("version_number"))

    @decorators.idempotent_id('e6b865d8-ffa8-4cfc-8afb-820c64f9b2af')
    def test_get_all_by_admin(self):
        """Admin user can list normal user's function version."""
        function_id = self.create_function()
        version = self.create_function_version(function_id)

        resp, body = self.admin_client.get_function_versions(function_id)

        self.assertEqual(200, resp.status)
        self.assertIn(
            version,
            [v['version_number'] for v in body['function_versions']]
        )

    @decorators.idempotent_id('0e70ef18-687c-4ce4-ae29-aee2f88b4b9c')
    def test_delete(self):
        function_id = self.create_function()
        version = self.create_function_version(function_id)

        resp = self.client.delete_function_version(function_id, version)

        self.assertEqual(204, resp.status)

        resp, body = self.client.get_function_versions(function_id)

        self.assertEqual(200, resp.status)
        self.assertNotIn(
            version,
            [v['version_number'] for v in body['function_versions']]
        )

    @decorators.idempotent_id('c6717e2e-e80a-43d9-a25b-84f4b7453c76')
    def test_delete_by_admin(self):
        """test_delete_by_admin

        Admin user can not delete normal user's function version.
        """
        function_id = self.create_function()
        version = self.create_function_version(function_id)

        self.assertRaises(
            exceptions.NotFound,
            self.admin_client.delete_function_version,
            function_id,
            version
        )

    @decorators.idempotent_id('7898f89f-a490-42a3-8cf7-63cbd9543a06')
    def test_detach(self):
        """Admin only operation."""
        function_id = self.create_function()
        version = self.create_function_version(function_id)

        # Create execution to allocate worker
        resp, _ = self.client.create_execution(
            function_id, input='{"name": "Qinling"}', version=version
        )
        self.assertEqual(201, resp.status)

        resp, body = self.admin_client.get_function_workers(function_id,
                                                            version=version)
        self.assertEqual(200, resp.status)
        self.assertEqual(1, len(body['workers']))

        # Detach function version from workers
        resp, _ = self.admin_client.detach_function(function_id,
                                                    version=version)
        self.assertEqual(202, resp.status)

        def _assert_workers():
            resp, body = self.admin_client.get_function_workers(
                function_id,
                version=version
            )
            self.assertEqual(200, resp.status)
            self.assertEqual(0, len(body['workers']))

        r = tenacity.Retrying(
            wait=tenacity.wait_fixed(1),
            stop=tenacity.stop_after_attempt(5),
            retry=tenacity.retry_if_exception_type(AssertionError)
        )
        r.call(_assert_workers)
