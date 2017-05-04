# Copyright 2017 Catalyst IT Limited
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

import jinja2
from kubernetes import config
from kubernetes import client
from kubernetes.client import models
from kubernetes.client.rest import ApiException
from oslo_config import cfg
from oslo_log import log as logging
import yaml

from qinling.orchestrator import base
from qinling.utils import common

LOG = logging.getLogger(__name__)

TEMPLATES_DIR = (os.path.dirname(os.path.realpath(__file__)) + '/templates/')


class KubernetesManager(base.OrchestratorBase):
    def __init__(self, conf):
        self.conf = conf

        client.Configuration().host = self.conf.kubernetes.kube_host
        self.v1 = client.CoreV1Api()
        self.v1extention = client.ExtensionsV1beta1Api()

        # Create namespace if not exists
        self._ensure_namespace()

        # Get templates.
        template_loader = jinja2.FileSystemLoader(
            searchpath=os.path.dirname(TEMPLATES_DIR)
        )
        jinja_env = jinja2.Environment(
            loader=template_loader, autoescape=True, trim_blocks=True
        )

        self.deployment_template = jinja_env.get_template('deployment.j2')

    def _ensure_namespace(self):
        ret = self.v1.list_namespace()
        cur_names = [i.metadata.name for i in ret.items]

        if self.conf.kubernetes.namespace not in cur_names:
            LOG.info('Creating namespace: %s', self.conf.kubernetes.namespace)

            namespace_body = {
                'apiVersion': 'v1',
                'kind': 'Namespace',
                'metadata': {
                    'name': self.conf.kubernetes.namespace,
                    'labels': {
                        'name': self.conf.kubernetes.namespace
                    }
                },
            }

            self.v1.create_namespace(namespace_body)

            LOG.info('Namespace %s created.', self.conf.kubernetes.namespace)

    def create_pool(self, name, image, labels=None):
        deployment_body = self.deployment_template.render(
            {
                "name": name,
                "labels": labels if labels else {},
                "replicas": self.conf.kubernetes.replicas,
                "volume_name": self.conf.kubernetes.volume_name,
                "container_name": 'worker',
                "image": image,
            }
        )

        LOG.info(
            "Creating deployment for runtime %s: \n%s", name, deployment_body
        )

        self.v1extention.create_namespaced_deployment(
            body=yaml.safe_load(deployment_body),
            namespace=self.conf.kubernetes.namespace
        )

        LOG.info("Deployment for runtime %s created.", name)

    def delete_pool(self, name, labels=None):
        """Delete all resources belong to the deployment."""

        LOG.info("Deleting deployment %s", name)

        selector = common.convert_dict_to_string(labels)

        self.v1.delete_collection_namespaced_pod(
            self.conf.kubernetes.namespace,
            label_selector=selector
        )

        LOG.info("Pods in deployment %s deleted.", name)

        self.v1extention.delete_collection_namespaced_replica_set(
            self.conf.kubernetes.namespace,
            label_selector=selector
        )

        LOG.info("ReplicaSets in deployment %s deleted.", name)

        ret = self.v1.list_namespaced_service(
            self.conf.kubernetes.namespace, label_selector=selector
        )
        names = [i.metadata.name for i in ret.items]
        for name in names:
            self.v1.delete_namespaced_service(
                name,
                self.conf.kubernetes.namespace,
                models.v1_delete_options.V1DeleteOptions()
            )

        LOG.info("Services in deployment %s deleted.", name)

        self.v1extention.delete_collection_namespaced_deployment(
            self.conf.kubernetes.namespace,
            label_selector=selector,
            field_selector='metadata.name=%s' % name
        )

        LOG.info("Deployment %s deleted.", name)
