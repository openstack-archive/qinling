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
        self.v1extension = clients['v1extension']
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
        reraise=True,
        retry=tenacity.retry_if_exception_type(exc.OrchestratorException)
    )
    def _wait_deployment_available(self, name):
        ret = self.v1extension.read_namespaced_deployment(
            name,
            self.conf.kubernetes.namespace
        )

        if (not ret.status.replicas or
                ret.status.replicas != ret.status.available_replicas):
            raise exc.OrchestratorException('Deployment %s not ready.' % name)

    def get_pool(self, name):
        total = 0
        available = 0

        try:
            ret = self.v1extension.read_namespaced_deployment(
                name,
                namespace=self.conf.kubernetes.namespace
            )
        except Exception:
            raise exc.RuntimeNotFoundException()

        if not ret.status.replicas:
            return {"total": total, "available": available}

        total = ret.status.replicas

        labels = {'runtime_id': name}
        selector = common.convert_dict_to_string(labels)
        ret = self.v1.list_namespaced_pod(
            self.conf.kubernetes.namespace,
            label_selector='!function_id,%s' % selector
        )
        available = len(ret.items)

        return {"total": total, "available": available}

    def create_pool(self, name, image, trusted=True):
        deployment_body = self.deployment_template.render(
            {
                "name": name,
                "labels": {'runtime_id': name},
                "replicas": self.conf.kubernetes.replicas,
                "container_name": 'worker',
                "image": image,
                "sidecar_image": self.conf.engine.sidecar_image,
                "trusted": str(trusted).lower()
            }
        )

        LOG.info(
            "Creating deployment for runtime %s: \n%s", name, deployment_body
        )

        self.v1extension.create_namespaced_deployment(
            body=yaml.safe_load(deployment_body),
            namespace=self.conf.kubernetes.namespace,
            async_req=False
        )

        self._wait_deployment_available(name)

        LOG.info("Deployment for runtime %s created.", name)

    def delete_pool(self, name):
        """Delete all resources belong to the deployment."""
        LOG.info("Deleting deployment %s", name)

        labels = {'runtime_id': name}
        selector = common.convert_dict_to_string(labels)

        self.v1extension.delete_collection_namespaced_replica_set(
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
                self.conf.kubernetes.namespace
            )
        LOG.info("Services in deployment %s deleted.", name)

        self.v1extension.delete_collection_namespaced_deployment(
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

    @tenacity.retry(
        wait=tenacity.wait_fixed(5),
        stop=tenacity.stop_after_delay(600),
        reraise=True,
        retry=tenacity.retry_if_exception_type(exc.OrchestratorException)
    )
    def _wait_for_upgrade(self, deploy_name):
        ret = self.v1extension.read_namespaced_deployment(
            deploy_name,
            self.conf.kubernetes.namespace
        )
        if ret.status.unavailable_replicas is not None:
            raise exc.OrchestratorException("Deployment %s upgrade not "
                                            "ready." % deploy_name)

    def update_pool(self, name, image=None):
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
                                'name': 'worker',
                                'image': image
                            }
                        ]
                    }
                }
            }
        }
        self.v1extension.patch_namespaced_deployment(
            name, self.conf.kubernetes.namespace, body
        )

        try:
            time.sleep(10)
            self._wait_for_upgrade(name)
        except exc.OrchestratorException:
            LOG.warn("Timeout when waiting for the deployment %s upgrade, "
                     "Start to roll back.", name)

            body = {"rollbackTo": {"revision": 0}}
            try:
                self.v1extension.create_namespaced_deployment_rollback(
                    name, self.conf.kubernetes.namespace, body
                )
            except Exception:
                # TODO(lxkong): remove the exception catch until kubernetes
                # python lib has a new release. Refer to
                # https://github.com/kubernetes-client/python/issues/491
                pass

            return False

        return True

    def _choose_available_pods(self, labels, count=1, function_id=None,
                               function_version=0):
        # If there is already a pod for function, reuse it.
        if function_id:
            ret = self.v1.list_namespaced_pod(
                self.conf.kubernetes.namespace,
                label_selector='function_id=%s,function_version=%s' %
                               (function_id, function_version)
            )
            if len(ret.items) >= count:
                LOG.debug(
                    "Function %s(version %s) already associates to a pod with "
                    "at least %d worker(s). ",
                    function_id, function_version, count
                )
                return ret.items[:count]

        selector = common.convert_dict_to_string(labels)
        ret = self.v1.list_namespaced_pod(
            self.conf.kubernetes.namespace,
            label_selector='!function_id,%s' % selector
        )

        if len(ret.items) < count:
            return []

        return ret.items[-count:]

    def _prepare_pod(self, pod, deployment_name, function_id, version,
                     labels=None):
        """Pod preparation.

        1. Update pod labels.
        2. Expose service.
        """
        pod_name = pod.metadata.name
        labels = labels or {}

        LOG.info(
            'Prepare pod %s in deployment %s for function %s(version %s)',
            pod_name, deployment_name, function_id, version
        )

        # Update pod label.
        pod_labels = self._update_pod_label(
            pod,
            # pod label value should be string
            {'function_id': function_id, 'function_version': str(version)}
        )

        # Create service for the chosen pod.
        service_name = "service-%s-%s" % (function_id, version)
        labels.update(
            {'function_id': function_id, 'function_version': str(version)}
        )

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

    def _create_pod(self, image, rlimit, pod_name, labels, input):
        """Create pod for image type function."""
        if not input:
            input_list = []
        elif isinstance(input, dict) and input.get('__function_input'):
            input_list = input.get('__function_input').split()
        else:
            input_list = list(json.loads(input))

        pod_body = self.pod_template.render(
            {
                "pod_name": pod_name,
                "labels": labels,
                "pod_image": image,
                "input": input_list,
                "req_cpu": str(rlimit['cpu']),
                "limit_cpu": str(rlimit['cpu']),
                "req_memory": str(rlimit['memory_size']),
                "limit_memory": str(rlimit['memory_size'])
            }
        )

        LOG.info(
            "Creating pod %s for image function:\n%s", pod_name, pod_body
        )

        try:
            self.v1.create_namespaced_pod(
                self.conf.kubernetes.namespace,
                body=yaml.safe_load(pod_body),
            )
        except Exception:
            LOG.exception("Failed to create pod.")
            raise exc.OrchestratorException('Execution preparation failed.')

    def _update_pod_label(self, pod, new_label):
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

    def prepare_execution(self, function_id, version, rlimit=None, image=None,
                          identifier=None, labels=None, input=None):
        """Prepare service URL for function version.

        :param rlimit: optional argument passed to limit cpu/mem resources.

        For image function, create a single pod with rlimit and input, so the
        function will be executed in the resource limited pod.

        For normal function, choose a pod from the pool and expose a service,
        return the service URL.

        return a tuple includes pod name and the servise url.
        """
        pods = None

        labels = labels or {'function_id': function_id}

        if image:
            if not rlimit:
                LOG.critical('Param rlimit is required for image function.')
                raise exc.OrchestratorException(
                    'Execution preparation failed.'
                )

            self._create_pod(image, rlimit, identifier, labels, input)

            return identifier, None
        else:
            pods = self._choose_available_pods(labels, function_id=function_id,
                                               function_version=version)

        if not pods:
            LOG.critical('No worker available.')
            raise exc.OrchestratorException('Execution preparation failed.')

        try:
            pod_name, url = self._prepare_pod(
                pods[0], identifier, function_id, version, labels
            )
            return pod_name, url
        except Exception:
            LOG.exception('Pod preparation failed.')
            self.delete_function(function_id, version, labels)
            raise exc.OrchestratorException('Execution preparation failed.')

    def run_execution(self, execution_id, function_id, version, rlimit=None,
                      input=None, identifier=None, service_url=None,
                      entry='main.main', trust_id=None, timeout=None):
        """Run execution.

        Return a tuple including the result and the output.
        """
        if service_url:
            func_url = '%s/execute' % service_url
            data = utils.get_request_data(
                self.conf, function_id, version, execution_id, rlimit, input,
                entry, trust_id, self.qinling_endpoint, timeout
            )
            LOG.debug(
                'Invoke function %s(version %s), url: %s, data: %s',
                function_id, version, func_url, data
            )

            return utils.url_request(self.session, func_url, body=data)
        else:
            # Wait for image type function execution to be finished
            def _wait_complete():
                pod = self.v1.read_namespaced_pod(
                    identifier,
                    self.conf.kubernetes.namespace
                )
                status = pod.status.phase

                if status == 'Succeeded':
                    return pod

                raise exc.TimeoutException()

            duration = 0
            try:
                r = tenacity.Retrying(
                    wait=tenacity.wait_fixed(1),
                    stop=tenacity.stop_after_delay(timeout),
                    retry=tenacity.retry_if_exception_type(
                        exc.TimeoutException),
                    reraise=True
                )
                pod = r.call(_wait_complete)

                statuses = pod.status.container_statuses
                for s in statuses:
                    if hasattr(s.state, "terminated"):
                        end_time = s.state.terminated.finished_at
                        start_time = s.state.terminated.started_at
                        delta = end_time - start_time
                        duration = delta.seconds
                        break
            except exc.TimeoutException:
                LOG.exception(
                    "Timeout for function execution %s, pod %s",
                    execution_id, identifier
                )

                self.v1.delete_namespaced_pod(
                    identifier,
                    self.conf.kubernetes.namespace
                )
                LOG.debug('Pod %s deleted.', identifier)

                return False, {'output': 'Function execution timeout.',
                               'duration': timeout}
            except Exception:
                LOG.exception("Failed to wait for pod %s", identifier)
                return False, {'output': 'Function execution failed.',
                               'duration': duration}

            log = self.v1.read_namespaced_pod_log(
                identifier,
                self.conf.kubernetes.namespace,
            )

            return True, {'duration': duration, 'logs': log}

    def delete_function(self, function_id, version, labels=None):
        """Delete related resources for function.

        - Delete service
        - Delete pods
        """
        pre_label = {
            'function_id': function_id,
            'function_version': str(version)
        }
        labels = labels or pre_label
        selector = common.convert_dict_to_string(labels)

        ret = self.v1.list_namespaced_service(
            self.conf.kubernetes.namespace, label_selector=selector
        )
        names = [i.metadata.name for i in ret.items]
        for svc_name in names:
            self.v1.delete_namespaced_service(
                svc_name,
                self.conf.kubernetes.namespace
            )

        self.v1.delete_collection_namespaced_pod(
            self.conf.kubernetes.namespace,
            label_selector=selector
        )

    def scaleup_function(self, function_id, version, identifier=None, count=1):
        pod_names = []
        labels = {'runtime_id': identifier}
        pods = self._choose_available_pods(labels, count=count)

        if not pods:
            raise exc.OrchestratorException('Not enough workers available.')

        for pod in pods:
            pod_name, service_url = self._prepare_pod(
                pod, identifier, function_id, version, labels
            )
            pod_names.append(pod_name)

        LOG.info('Pods scaled up for function %s(version %s): %s', function_id,
                 version, pod_names)

        return pod_names, service_url

    def delete_worker(self, pod_name, **kwargs):
        self.v1.delete_namespaced_pod(
            pod_name,
            self.conf.kubernetes.namespace,
        )
