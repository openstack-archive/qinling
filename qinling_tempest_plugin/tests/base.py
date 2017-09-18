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
from kubernetes import client as k8s_client
from tempest import config
from tempest import test
import tenacity

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
        k8s_client.Configuration().host = CONF.qinling.kube_host
        cls.k8s_v1 = k8s_client.CoreV1Api()
        cls.k8s_v1extention = k8s_client.ExtensionsV1beta1Api()
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
