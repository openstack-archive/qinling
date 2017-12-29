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

from tempest import config
from tempest.lib.common.utils import data_utils
from tempest import test
import tenacity

from qinling_tempest_plugin.tests import utils

CONF = config.CONF


class BaseQinlingTest(test.BaseTestCase):
    credentials = ('admin', 'primary', 'alt')

    @classmethod
    def skip_checks(cls):
        super(BaseQinlingTest, cls).skip_checks()

        if not CONF.service_available.qinling:
            raise cls.skipException("Qinling service is not available.")

    @classmethod
    def setup_clients(cls):
        super(BaseQinlingTest, cls).setup_clients()

        cls.client = cls.os_primary.qinling.QinlingClient()
        cls.alt_client = cls.os_alt.qinling.QinlingClient()
        cls.admin_client = cls.os_admin.qinling.QinlingClient()

        # Initilize k8s client
        clients = utils.get_k8s_clients(CONF)
        cls.k8s_v1 = clients['v1']
        cls.k8s_v1extention = clients['v1extention']
        cls.namespace = 'qinling'

    @tenacity.retry(
        wait=tenacity.wait_fixed(3),
        stop=tenacity.stop_after_attempt(10),
        retry=tenacity.retry_if_exception_type(AssertionError)
    )
    def await_runtime_available(self, id):
        resp, body = self.client.get_resource('runtimes', id)

        self.assertEqual(200, resp.status)
        self.assertEqual('available', body['status'])

    @tenacity.retry(
        wait=tenacity.wait_fixed(3),
        stop=tenacity.stop_after_attempt(10),
        retry=tenacity.retry_if_exception_type(AssertionError)
    )
    def await_execution_success(self, id):
        resp, body = self.client.get_resource('executions', id)

        self.assertEqual(200, resp.status)
        self.assertEqual('success', body['status'])

    def create_function(self, package_path=None, image=False):
        function_name = data_utils.rand_name('function',
                                             prefix=self.name_prefix)

        if not image:
            base_name, _ = os.path.splitext(package_path)
            module_name = os.path.basename(base_name)
            with open(package_path, 'rb') as package_data:
                resp, body = self.client.create_function(
                    {"source": "package"},
                    self.runtime_id,
                    name=function_name,
                    package_data=package_data,
                    entry='%s.main' % module_name
                )
            self.addCleanup(os.remove, package_path)
        else:
            resp, body = self.client.create_function(
                {"source": "image", "image": "openstackqinling/alpine-test"},
                None,
                name=function_name,
            )

        self.assertEqual(201, resp.status_code)
        function_id = body['id']
        self.addCleanup(self.client.delete_resource, 'functions',
                        function_id, ignore_notfound=True)

        return function_id
