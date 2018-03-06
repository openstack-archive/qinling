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

import copy
import json
import os
import time

import jinja2
from oslo_log import log as logging
import requests
import tenacity
import yaml

from qinling.engine import utils
from qinling import exceptions as exc
from qinling.orchestrator import base
from qinling.orchestrator.kubernetes import utils as k8s_util
from qinling.utils import common

LOG = logging.getLogger(__name__)

TEMPLATES_DIR = (os.path.dirname(os.path.realpath(__file__)) + '/templates/')


class KubernetesManager(base.OrchestratorBase):
    def __init__(self, conf, qinling_endpoint):
        self.conf = conf
        self.qinling_endpoint = qinling_endpoint

        clients = k8s_util.get_k8s_clients(self.conf)
        self.v1 = clients['v1']
        self.v1extention = clients['v1extention']
        # self.apps_v1 = clients['apps_v1']

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

        # Refer to
        # http://docs.python-requests.org/en/master/user/advanced/#session-objects
        self.session = requests.Session()

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

    @tenacity.retry(
        wait=tenacity.wait_fixed(2),
        stop=tenacity.stop_after_delay(600),
        retry=tenacity.retry_if_result(lambda result: not result)
    )
    def _wait_deployment_available(self, name):
        ret = self.v1extention.read_namespaced_deployment(
            name,
            self.conf.kubernetes.namespace
        )

        if not ret.status.replicas:
            return False

        return ret.status.replicas == ret.status.available_replicas

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

        self._wait_deployment_available(name)

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

    def _choose_available_pod(self, labels, count=1, function_id=None):
        selector = common.convert_dict_to_string(labels)

        # If there is already a pod for function, reuse it.
        if function_id:
            ret = self.v1.list_namespaced_pod(
                self.conf.kubernetes.namespace,
                label_selector='function_id=%s' % function_id
            )
            if len(ret.items) > 0:
                LOG.debug(
                    "Function %s already associates to a pod.", function_id
                )
                return ret.items[:count]

        ret = self.v1.list_namespaced_pod(
            self.conf.kubernetes.namespace,
            label_selector='!function_id,%s' % selector
        )

        if len(ret.items) == 0:
            return None

        return ret.items[-count:]

    def _prepare_pod(self, pod, deployment_name, function_id, labels=None):
        """Pod preparation.

        1. Update pod labels.
        2. Expose service.
        """
        pod_name = pod.metadata.name
        labels = labels or {}

        LOG.info(
            'Prepare pod %s in deployment %s for function %s',
            pod_name, deployment_name, function_id
        )

        # Update pod label.
        pod_labels = self._update_pod_label(pod, {'function_id': function_id})

        # Create service for the chosen pod.
        service_name = "service-%s" % function_id
        labels.update({'function_id': function_id})

        # TODO(kong): Make the service type configurable.
        service_body = self.service_template.render(
            {
                "service_name": service_name,
                "labels": labels,
                "selector": pod_labels
            }
        )
        try:
            ret = self.v1.create_namespaced_service(
                self.conf.kubernetes.namespace, yaml.safe_load(service_body)
            )
            LOG.debug(
                'Service created for pod %s, service name: %s',
                pod_name, service_name
            )
        except Exception as e:
            # Service already exists
            if e.status == 409:
                LOG.debug(
                    'Service already exists for pod %s, service name: %s',
                    pod_name, service_name
                )
                time.sleep(1)
                ret = self.v1.read_namespaced_service(
                    service_name, self.conf.kubernetes.namespace
                )
            else:
                raise

        # Get external ip address for an arbitrary node.
        node_port = ret.spec.ports[0].node_port
        nodes = self.v1.list_node()
        addresses = nodes.items[0].status.addresses
        node_ip = None
        for addr in addresses:
            if addr.type == 'ExternalIP':
                node_ip = addr.address

        # FIXME: test purpose using minikube
        if not node_ip:
            for addr in addresses:
                if addr.type == 'InternalIP':
                    node_ip = addr.address

        pod_service_url = 'http://%s:%s' % (node_ip, node_port)

        return pod_name, pod_service_url

    def _create_pod(self, image, pod_name, labels, input):
        if not input:
            input_list = []
        elif input.get('__function_input'):
            input_list = input.get('__function_input').split()
        else:
            input_list = [json.dumps(input)]

        pod_body = self.pod_template.render(
            {
                "pod_name": pod_name,
                "labels": labels,
                "pod_image": image,
                "input": input_list
            }
        )

        LOG.info(
            "Creating pod %s for image function:\n%s", pod_name, pod_body
        )

        self.v1.create_namespaced_pod(
            self.conf.kubernetes.namespace,
            body=yaml.safe_load(pod_body),
        )

    def _update_pod_label(self, pod, new_label=None):
        name = pod.metadata.name

        pod_labels = copy.deepcopy(pod.metadata.labels) or {}
        pod_labels.update(new_label)
        body = {
            'metadata': {
                'labels': pod_labels
            }
        }
        self.v1.patch_namespaced_pod(
            name, self.conf.kubernetes.namespace, body
        )

        LOG.debug('Labels updated for pod %s', name)

        return pod_labels

    def prepare_execution(self, function_id, image=None, identifier=None,
                          labels=None, input=None):
        """Prepare service URL for function.

        For image function, create a single pod with input, so the function
        will be executed.

        For normal function, choose a pod from the pool and expose a service,
        return the service URL.
        """
        pod = None

        if image:
            self._create_pod(image, identifier, labels, input)
            return identifier, None
        else:
            pod = self._choose_available_pod(labels, function_id=function_id)

        if not pod:
            LOG.critical('No worker available.')
            raise exc.OrchestratorException('Execution preparation failed.')

        try:
            pod_name, url = self._prepare_pod(
                pod[0], identifier, function_id, labels
            )
            return pod_name, url
        except Exception:
            LOG.exception('Pod preparation failed.')
            self.delete_function(function_id, labels)
            raise exc.OrchestratorException('Execution preparation failed.')

    def run_execution(self, execution_id, function_id, input=None,
                      identifier=None, service_url=None, entry='main.main',
                      trust_id=None):
        """Run execution and get output."""
        if service_url:
            func_url = '%s/execute' % service_url
            data = utils.get_request_data(
                self.conf, function_id, execution_id, input, entry, trust_id,
                self.qinling_endpoint
            )
            LOG.debug(
                'Invoke function %s, url: %s, data: %s',
                function_id, func_url, data
            )

            return utils.url_request(self.session, func_url, body=data)
        else:
            def _wait_complete():
                pod = self.v1.read_namespaced_pod(
                    identifier,
                    self.conf.kubernetes.namespace
                )
                status = pod.status.phase
                return True if status == 'Succeeded' else False

            try:
                r = tenacity.Retrying(
                    wait=tenacity.wait_fixed(1),
                    stop=tenacity.stop_after_delay(180),
                    retry=tenacity.retry_if_result(
                        lambda result: result is False)
                )
                r.call(_wait_complete)
            except Exception as e:
                LOG.exception(
                    "Failed to get pod output, pod: %s, error: %s",
                    identifier, str(e)
                )
                return False, {'error': 'Function execution failed.'}

            output = self.v1.read_namespaced_pod_log(
                identifier,
                self.conf.kubernetes.namespace,
            )
            return True, output

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

        self.v1.delete_collection_namespaced_pod(
            self.conf.kubernetes.namespace,
            label_selector=selector
        )

    def scaleup_function(self, function_id, identifier=None, count=1):
        pod_names = []
        labels = {'runtime_id': identifier}
        pods = self._choose_available_pod(labels, count=count)

        if not pods:
            raise exc.OrchestratorException('Not enough workers available.')

        for pod in pods:
            pod_name, service_url = self._prepare_pod(
                pod, identifier, function_id, labels
            )
            pod_names.append(pod_name)

        LOG.info('Pods scaled up for function %s: %s', function_id, pod_names)
        return pod_names, service_url

    def delete_worker(self, pod_name, **kwargs):
        self.v1.delete_namespaced_pod(
            pod_name,
            self.conf.kubernetes.namespace,
            {}
        )
