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

CONF = config.CONF


class BaseQinlingTest(test.BaseTestCase):
    credentials = ('primary',)
    force_tenant_isolation = False

    @classmethod
    def skip_checks(cls):
        super(BaseQinlingTest, cls).skip_checks()

        if not CONF.service_available.qinling:
            raise cls.skipException("Qinling service is not available.")

    @classmethod
    def setup_clients(cls):
        super(BaseQinlingTest, cls).setup_clients()

        # os here is tempest.lib.services.clients.ServiceClients object
        os = getattr(cls, 'os_%s' % cls.credentials[0])
        cls.qinling_client = os.qinling.QinlingClient()

        if CONF.identity.auth_version == 'v3':
            project_id = os.auth_provider.auth_data[1]['project']['id']
        else:
            project_id = os.auth_provider.auth_data[1]['token']['tenant']['id']
        cls.tenant_id = project_id
        cls.user_id = os.auth_provider.auth_data[1]['user']['id']

        # Initilize k8s client
        k8s_client.Configuration().host = CONF.qinling.kube_host
        cls.k8s_v1 = k8s_client.CoreV1Api()
        cls.k8s_v1extention = k8s_client.ExtensionsV1beta1Api()
        cls.namespace = 'qinling'
