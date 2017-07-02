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
import time

import jinja2
from kubernetes import client
from oslo_log import log as logging
import requests
import yaml

from qinling import context
from qinling import exceptions as exc
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
            loader=template_loader, autoescape=True, trim_blocks=True,
            lstrip_blocks=True
        )
        self.deployment_template = jinja_env.get_template('deployment.j2')
        self.service_template = jinja_env.get_template('service.j2')
        self.pod_template = jinja_env.get_template('pod.j2')

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

        self.v1extention.delete_collection_namespaced_replica_set(
            self.conf.kubernetes.namespace,
            label_selector=selector
        )

        LOG.info("ReplicaSets in deployment %s deleted.", name)

        ret = self.v1.list_namespaced_service(
            self.conf.kubernetes.namespace, label_selector=selector
        )
        names = [i.metadata.name for i in ret.items]
        for svc_name in names:
            self.v1.delete_namespaced_service(
                svc_name,
                self.conf.kubernetes.namespace,
            )

        LOG.info("Services in deployment %s deleted.", name)

        self.v1extention.delete_collection_namespaced_deployment(
            self.conf.kubernetes.namespace,
            label_selector=selector,
            field_selector='metadata.name=%s' % name
        )

        # Should delete pods after deleting deployment to avoid pods are
        # recreated by k8s.
        self.v1.delete_collection_namespaced_pod(
            self.conf.kubernetes.namespace,
            label_selector=selector
        )

        LOG.info("Pods in deployment %s deleted.", name)
        LOG.info("Deployment %s deleted.", name)

    def update_pool(self, name, labels=None, image=None):
        """Deployment rolling-update.

        Return True if successful, otherwise return False after rolling back.
        """
        LOG.info('Start to do rolling-update deployment %s', name)

        body = {
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            {
                                # TODO(kong): Make the name configurable.
                                'name': 'worker',
                                'image': image
                            }
                        ]
                    }
                }
            }
        }
        self.v1extention.patch_namespaced_deployment(
            name, self.conf.kubernetes.namespace, body
        )

        unavailable_replicas = 1
        # TODO(kong): Make this configurable
        retry = 5
        while unavailable_replicas != 0 and retry > 0:
            time.sleep(5)
            retry = retry - 1

            deploy = self.v1extention.read_namespaced_deployment_status(
                name,
                self.conf.kubernetes.namespace
            )
            unavailable_replicas = deploy.status.unavailable_replicas

        # Handle failure of rolling-update.
        if unavailable_replicas > 0:
            body = {
                "name": name,
                "rollbackTo": {
                    "revision": 0
                }
            }
            self.v1extention.create_namespaced_deployment_rollback_rollback(
                name, self.conf.kubernetes.namespace, body
            )

            return False

        return True

    def _choose_available_pod(self, labels):
        selector = common.convert_dict_to_string(labels)

        ret = self.v1.list_namespaced_pod(
            self.conf.kubernetes.namespace,
            label_selector='!function_id,%s' % selector
        )

        if len(ret.items) == 0:
            return None

        # Choose the last available one by default.
        pod = ret.items[-1]

        return pod

    def _prepare_pod(self, pod, deployment_name, function_id, labels, entry):
        """Pod preparation.

        1. Update pod labels.
        2. Expose service and trigger package download.
        """
        name = pod.metadata.name

        LOG.info(
            'Prepare pod %s in deployment %s for function %s',
            name, deployment_name, function_id
        )

        # Update pod label.
        pod_labels = pod.metadata.labels or {}
        pod_labels.update({'function_id': function_id})
        body = {
            'metadata': {
                'labels': pod_labels
            }
        }
        self.v1.patch_namespaced_pod(
            name, self.conf.kubernetes.namespace, body
        )

        LOG.debug('Labels updated for pod %s', name)

        # Create service for the choosen pod.
        service_name = "service-%s" % function_id
        labels.update({'function_id': function_id})
        service_body = self.service_template.render(
            {
                "service_name": service_name,
                "labels": labels,
                "selector": pod_labels
            }
        )
        ret = self.v1.create_namespaced_service(
            self.conf.kubernetes.namespace, yaml.safe_load(service_body)
        )
        node_port = ret.spec.ports[0].node_port

        LOG.debug(
            'Service created for pod %s, service name: %s, node port: %s',
            name, service_name, node_port
        )

        # Get external ip address for an arbitary node.
        ret = self.v1.list_node()
        addresses = ret.items[0].status.addresses
        node_ip = None
        for addr in addresses:
            if addr.type == 'ExternalIP':
                node_ip = addr.address

        # FIXME: test purpose using minikube
        if not node_ip:
            for addr in addresses:
                if addr.type == 'InternalIP':
                    node_ip = addr.address

        # Download code package into container.
        pod_service_url = 'http://%s:%s' % (node_ip, node_port)
        request_url = '%s/download' % pod_service_url
        download_url = (
            'http://%s:%s/v1/functions/%s?download=true' %
            (self.conf.kubernetes.qinling_service_address,
             self.conf.api.port, function_id)
        )

        data = {
            'download_url': download_url,
            'function_id': function_id,
            'entry': entry,
            'token': context.get_ctx().auth_token,
            'auth_url': self.conf.keystone_authtoken.auth_url
        }

        LOG.debug(
            'Send request to pod %s, request_url: %s, data: %s',
            name, request_url, data
        )

        # TODO(kong): Here we sleep some time to avoid 'Failed to establish a
        # new connection' error for some reason. Needs to find a better
        # solution.
        time.sleep(1)
        r = requests.post(request_url, data=data)

        if r.status_code != requests.codes.ok:
            raise exc.OrchestratorException(
                'Failed to download function code package.'
            )

        return pod_service_url

    def _create_pod(self, image, pod_name, labels, input):
        pod_body = self.pod_template.render(
            {
                "pod_name": pod_name,
                "labels": labels,
                "pod_image": image,
                "input": input
            }
        )

        LOG.info(
            "Creating pod %s for image function:\n%s", pod_name, pod_body
        )

        self.v1.create_namespaced_pod(
            self.conf.kubernetes.namespace,
            body=yaml.safe_load(pod_body),
        )

    def prepare_execution(self, function_id, image=None, identifier=None,
                          labels=None, input=None, entry='main.main'):
        """Prepare service URL for function.

        For image function, create a single pod with input, so the function
        will be executed.

        For normal function, choose a pod from the pool and expose a service,
        return the service URL.
        """
        pod = None

        if image:
            self._create_pod(image, identifier, labels, input)
            return None
        else:
            pod = self._choose_available_pod(labels)

        if not pod:
            raise exc.OrchestratorException('No pod available.')

        return self._prepare_pod(pod, identifier, function_id, labels, entry)

    def run_execution(self, function_id, input=None, identifier=None,
                      service_url=None):
        if service_url:
            func_url = '%s/execute' % service_url
            LOG.info('Invoke function %s, url: %s', function_id, func_url)

            r = requests.post(func_url, data=input)

            return {'result': r.json()}
        else:
            status = None

            # Wait for execution to be finished.
            # TODO(kong): Do not retry infinitely.
            while status != 'Succeeded':
                pod = self.v1.read_namespaced_pod(
                    identifier,
                    self.conf.kubernetes.namespace
                )
                status = pod.status.phase

                time.sleep(0.5)

            output = self.v1.read_namespaced_pod_log(
                identifier,
                self.conf.kubernetes.namespace,
            )

            return {'result': output}

    def delete_function(self, function_id, labels=None):
        selector = common.convert_dict_to_string(labels)

        ret = self.v1.list_namespaced_service(
            self.conf.kubernetes.namespace, label_selector=selector
        )
        names = [i.metadata.name for i in ret.items]
        for svc_name in names:
            self.v1.delete_namespaced_service(
                svc_name,
                self.conf.kubernetes.namespace,
            )

        LOG.info("Services for function %s deleted.", function_id)

        self.v1.delete_collection_namespaced_pod(
            self.conf.kubernetes.namespace,
            label_selector=selector
        )

        LOG.info("Pod for function %s deleted.", function_id)
