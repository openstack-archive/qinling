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


class RuntimesTest(base.BaseQinlingTest):
    name_prefix = 'RuntimesTest'
    create_runtime = False

    @decorators.idempotent_id('fdc2f07f-dd1d-4981-86d3-5bc7908d9a9b')
    def test_crud_runtime(self):
        name = data_utils.rand_name('runtime', prefix=self.name_prefix)
        resp, body = self.admin_client.create_runtime(self.image, name)

        self.assertEqual(201, resp.status)
        self.assertEqual(name, body['name'])

        runtime_id = body['id']
        self.addCleanup(self.admin_client.delete_resource, 'runtimes',
                        runtime_id, ignore_notfound=True)

        # Get runtimes
        resp, body = self.client.get_resources('runtimes')

        self.assertEqual(200, resp.status)
        self.assertIn(
            runtime_id,
            [runtime['id'] for runtime in body['runtimes']]
        )

        # Wait for runtime to be available
        # We don't have to check k8s resource, if runtime's status has changed
        # to available, then kubernetes deployment is assumed to be ok.
        self.wait_runtime_available(runtime_id)

        # Delete runtime
        resp = self.admin_client.delete_resource('runtimes', runtime_id)

        self.assertEqual(204, resp.status)

    @decorators.idempotent_id('c1db56bd-c3a8-4ca6-9482-c362fd492db0')
    def test_create_private_runtime(self):
        """Private runtime test.

        Admin user creates a private runtime which can not be used by other
        projects.
        """
        name = data_utils.rand_name('runtime', prefix=self.name_prefix)
        resp, body = self.admin_client.create_runtime(
            self.image, name, is_public=False
        )

        self.assertEqual(201, resp.status)
        self.assertEqual(name, body['name'])
        self.assertFalse(body['is_public'])

        runtime_id = body['id']
        self.addCleanup(self.admin_client.delete_resource, 'runtimes',
                        runtime_id, ignore_notfound=True)

        # Get runtimes
        resp, body = self.client.get_resources('runtimes')

        self.assertEqual(200, resp.status)
        self.assertNotIn(
            runtime_id,
            [runtime['id'] for runtime in body['runtimes']]
        )
