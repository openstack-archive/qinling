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
import tenacity

from qinling_tempest_plugin.tests import base


class RuntimesTest(base.BaseQinlingTest):
    name_prefix = 'RuntimesTest'

    @tenacity.retry(
        wait=tenacity.wait_fixed(2),
        stop=tenacity.stop_after_delay(10),
        retry=tenacity.retry_if_exception_type(AssertionError)
    )
    def _await_runtime_available(self, id):
        resp, body = self.qinling_client.get_obj('runtimes', id)

        self.assertEqual(200, resp.status)
        self.assertEqual('available', body['status'])

    @decorators.idempotent_id('fdc2f07f-dd1d-4981-86d3-5bc7908d9a9b')
    def test_create_list_get_delete_runtime(self):
        name = data_utils.rand_name('runtime', prefix=self.name_prefix)

        req_body = {
            'name': name,
            'image': 'openstackqinling/python-runtime'
        }
        resp, body = self.qinling_client.post_json('runtimes', req_body)
        runtime_id = body['id']

        self.assertEqual(201, resp.status)
        self.assertEqual(name, body['name'])

        # Get runtimes
        resp, body = self.qinling_client.get_list_objs('runtimes')

        self.assertEqual(200, resp.status)
        self.assertIn(
            runtime_id,
            [runtime['id'] for runtime in body['runtimes']]
        )

        # Wait for runtime to be available
        self._await_runtime_available(runtime_id)

        # Check k8s resource
        deploy = self.k8s_v1extention.read_namespaced_deployment(
            runtime_id,
            namespace=self.namespace
        )

        self.assertEqual(runtime_id, deploy.metadata.name)
        self.assertEqual(
            deploy.status.replicas, deploy.status.available_replicas
        )

        # Delete runtime
        resp, _ = self.qinling_client.delete_obj('runtimes', runtime_id)

        self.assertEqual(204, resp.status)
