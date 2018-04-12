# Copyright 2018 Catalyst IT Limited
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

from kubernetes.client import api_client
# from kubernetes.client.apis import apps_v1_api
from kubernetes.client.apis import core_v1_api
from kubernetes.client.apis import extensions_v1beta1_api
from kubernetes.client import configuration as k8s_config


def get_k8s_clients(conf):
    config = k8s_config.Configuration()
    config.host = conf.kubernetes.kube_host
    if conf.kubernetes.use_api_certificate:
        config.ssl_ca_cert = conf.kubernetes.ssl_ca_cert
        config.cert_file = conf.kubernetes.cert_file
        config.key_file = conf.kubernetes.key_file
    else:
        config.verify_ssl = False
    client = api_client.ApiClient(configuration=config)
    v1 = core_v1_api.CoreV1Api(client)
    v1extension = extensions_v1beta1_api.ExtensionsV1beta1Api(client)
    # apps_v1 = apps_v1_api.AppsV1Api(client)

    clients = {
        'v1': v1,
        # 'apps_v1': apps_v1
        'v1extension': v1extension
    }

    return clients
