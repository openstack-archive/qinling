# Copyright 2018 AWCloud Software Co., Ltd
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

import datetime
import testtools
from unittest import mock
import yaml

from oslo_config import cfg

from qinling import config
from qinling import exceptions as exc
from qinling.orchestrator.kubernetes import manager as k8s_manager
from qinling.tests.unit import base
from qinling.utils import common

CONF = cfg.CONF
SERVICE_PORT = 9090
SERVICE_ADDRESS_EXTERNAL = '1.2.3.4'
SERVICE_ADDRESS_INTERNAL = '127.0.0.1'


class TestKubernetesManager(base.DbTestCase):
    def setUp(self):
        super(TestKubernetesManager, self).setUp()

        self.conf = CONF
        self.qinling_endpoint = 'http://127.0.0.1:7070'
        self.rlimit = {
            'cpu': cfg.CONF.resource_limits.default_cpu,
            'memory_size': cfg.CONF.resource_limits.default_memory
        }
        self.k8s_v1_api = mock.Mock()
        self.k8s_v1_ext = mock.Mock()
        clients = {'v1': self.k8s_v1_api,
                   'v1extension': self.k8s_v1_ext}
        mock.patch(
            'qinling.orchestrator.kubernetes.utils.get_k8s_clients',
            return_value=clients
        ).start()
        self.fake_namespace = self.rand_name('namespace', prefix=self.prefix)
        self.override_config('namespace', self.fake_namespace,
                             config.KUBERNETES_GROUP)

        self.override_config('auth_enable', False, group='pecan')

        namespace = mock.Mock()
        namespace.metadata.name = self.fake_namespace
        namespaces = mock.Mock()
        namespaces.items = [namespace]
        self.k8s_v1_api.list_namespace.return_value = namespaces

        self.manager = k8s_manager.KubernetesManager(self.conf,
                                                     self.qinling_endpoint)

    def _create_service(self):
        port = mock.Mock()
        port.node_port = SERVICE_PORT
        service = mock.Mock()
        service.spec.ports = [port]
        return service

    def _create_nodes_with_external_ip(self):
        addr1 = mock.Mock()
        addr1.type = 'UNKNOWN TYPE'
        addr2 = mock.Mock()
        addr2.type = 'ExternalIP'
        addr2.address = SERVICE_ADDRESS_EXTERNAL
        item = mock.Mock()
        item.status.addresses = [addr1, addr2]
        nodes = mock.Mock()
        nodes.items = [item]
        return nodes

    def _create_nodes_with_internal_ip(self):
        addr1 = mock.Mock()
        addr1.type = 'InternalIP'
        addr1.address = SERVICE_ADDRESS_INTERNAL
        addr2 = mock.Mock()
        addr2.type = 'UNKNOWN TYPE'
        item = mock.Mock()
        item.status.addresses = [addr1, addr2]
        nodes = mock.Mock()
        nodes.items = [item]
        return nodes

    def test__ensure_namespace(self):
        # self.manager is not used in this test.
        namespaces = mock.Mock()
        namespaces.items = []
        self.k8s_v1_api.list_namespace.return_value = namespaces

        k8s_manager.KubernetesManager(self.conf, self.qinling_endpoint)

        namespace_body = {
            'apiVersion': 'v1',
            'kind': 'Namespace',
            'metadata': {
                'name': self.fake_namespace,
                'labels': {
                    'name': self.fake_namespace
                }
            },
        }
        # setUp also calls list_namespace.
        self.assertEqual(2, self.k8s_v1_api.list_namespace.call_count)
        self.k8s_v1_api.create_namespace.assert_called_once_with(
            namespace_body)

    def test__ensure_namespace_not_create_namespace(self):
        # self.manager is not used in this test.
        item = mock.Mock()
        item.metadata.name = self.fake_namespace
        namespaces = mock.Mock()
        namespaces.items = [item]
        self.k8s_v1_api.list_namespace.return_value = namespaces

        k8s_manager.KubernetesManager(self.conf, self.qinling_endpoint)

        # setUp also calls list_namespace.
        self.assertEqual(2, self.k8s_v1_api.list_namespace.call_count)
        self.k8s_v1_api.create_namespace.assert_not_called()

    def test_create_pool(self):
        ret = mock.Mock()
        ret.status.replicas = 5
        ret.status.available_replicas = 5
        self.k8s_v1_ext.read_namespaced_deployment.return_value = ret
        fake_replicas = 5
        self.override_config('replicas', fake_replicas,
                             config.KUBERNETES_GROUP)
        fake_deployment_name = self.rand_name('deployment', prefix=self.prefix)
        fake_image = self.rand_name('image', prefix=self.prefix)

        self.manager.create_pool(fake_deployment_name, fake_image)

        deployment_body = self.manager.deployment_template.render(
            {
                'name': fake_deployment_name,
                'labels': {'runtime_id': fake_deployment_name},
                'replicas': fake_replicas,
                'container_name': 'worker',
                'image': fake_image,
                'sidecar_image': CONF.engine.sidecar_image,
                'trusted': 'true'
            }
        )
        self.k8s_v1_ext.create_namespaced_deployment.assert_called_once_with(
            body=yaml.safe_load(deployment_body),
            namespace=self.fake_namespace,
            async_req=False)
        self.k8s_v1_ext.read_namespaced_deployment.assert_called_once_with(
            fake_deployment_name, self.fake_namespace)

    def test_create_pool_wait_deployment_available(self):
        ret1 = mock.Mock()
        ret1.status.replicas = 0
        ret2 = mock.Mock()
        ret2.status.replicas = 3
        ret2.status.available_replicas = 1
        ret3 = mock.Mock()
        ret3.status.replicas = 3
        ret3.status.available_replicas = 3
        self.k8s_v1_ext.read_namespaced_deployment.side_effect = [
            ret1, ret2, ret3
        ]
        fake_deployment_name = self.rand_name('deployment', prefix=self.prefix)
        fake_image = self.rand_name('image', prefix=self.prefix)

        self.manager.create_pool(fake_deployment_name, fake_image)

        self.assertEqual(
            3, self.k8s_v1_ext.read_namespaced_deployment.call_count)

    @testtools.skip("Default timeout is too long.")
    def test_create_pool_wait_deployment_timeout(self):
        ret = mock.Mock()
        ret.status.replicas = 0
        self.k8s_v1_ext.read_namespaced_deployment.return_value = ret
        fake_deployment_name = self.rand_name('deployment', prefix=self.prefix)
        fake_image = self.rand_name('image', prefix=self.prefix)

        self.assertRaisesRegex(
            exc.OrchestratorException,
            "^Deployment %s not ready\.$" % fake_deployment_name,
            self.manager.create_pool,
            fake_deployment_name, fake_image)
        self.assertLess(
            200,  # Default timeout is 600s with wait interval set to 2s.
            self.k8s_v1_ext.read_namespaced_deployment.call_count)

    def test_delete_pool(self):
        # Deleting namespaced service is also tested in this.
        svc1 = mock.Mock()
        svc1_name = self.rand_name('service', prefix=self.prefix)
        svc1.metadata.name = svc1_name
        svc2 = mock.Mock()
        svc2_name = self.rand_name('service', prefix=self.prefix)
        svc2.metadata.name = svc2_name
        services = mock.Mock()
        services.items = [svc1, svc2]
        self.k8s_v1_api.list_namespaced_service.return_value = services
        fake_deployment_name = self.rand_name('deployment', prefix=self.prefix)

        self.manager.delete_pool(fake_deployment_name)

        del_rep = self.k8s_v1_ext.delete_collection_namespaced_replica_set
        del_rep.assert_called_once_with(
            self.fake_namespace,
            label_selector='runtime_id=%s' % fake_deployment_name)
        delete_service_calls = [
            mock.call(svc1_name, self.fake_namespace),
            mock.call(svc2_name, self.fake_namespace),
        ]
        self.k8s_v1_api.delete_namespaced_service.assert_has_calls(
            delete_service_calls)
        self.assertEqual(
            2, self.k8s_v1_api.delete_namespaced_service.call_count)
        del_dep = self.k8s_v1_ext.delete_collection_namespaced_deployment
        del_dep.assert_called_once_with(
            self.fake_namespace,
            label_selector='runtime_id=%s' % fake_deployment_name,
            field_selector='metadata.name=%s' % fake_deployment_name)
        del_pod = self.k8s_v1_api.delete_collection_namespaced_pod
        del_pod.assert_called_once_with(
            self.fake_namespace,
            label_selector='runtime_id=%s' % fake_deployment_name)

    def test_update_pool(self):
        fake_deployment_name = self.rand_name('deployment', prefix=self.prefix)
        image = self.rand_name('image', prefix=self.prefix)
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
        ret = mock.Mock()
        ret.status.unavailable_replicas = None
        self.k8s_v1_ext.read_namespaced_deployment.return_value = ret

        update_result = self.manager.update_pool(fake_deployment_name,
                                                 image=image)

        self.assertTrue(update_result)
        self.k8s_v1_ext.patch_namespaced_deployment.assert_called_once_with(
            fake_deployment_name, self.fake_namespace, body)
        read_status = self.k8s_v1_ext.read_namespaced_deployment
        read_status.assert_called_once_with(fake_deployment_name,
                                            self.fake_namespace)

    def test_update_pool_retry(self):
        fake_deployment_name = self.rand_name('deployment', prefix=self.prefix)
        image = self.rand_name('image', prefix=self.prefix)
        ret1 = mock.Mock()
        ret1.status.unavailable_replicas = 1
        ret2 = mock.Mock()
        ret2.status.unavailable_replicas = None
        self.k8s_v1_ext.read_namespaced_deployment.side_effect = [ret1, ret2]

        update_result = self.manager.update_pool(fake_deployment_name,
                                                 image=image)

        self.assertTrue(update_result)
        self.k8s_v1_ext.patch_namespaced_deployment.assert_called_once_with(
            fake_deployment_name, self.fake_namespace, mock.ANY)
        read_status = self.k8s_v1_ext.read_namespaced_deployment
        self.assertEqual(2, read_status.call_count)

    def test_get_pool(self):
        fake_deployment_name = self.rand_name('deployment', prefix=self.prefix)

        ret = mock.Mock()
        ret.status.replicas = 3
        self.k8s_v1_ext.read_namespaced_deployment.return_value = ret

        list_pod_ret = mock.Mock()
        list_pod_ret.items = [mock.Mock()]
        self.k8s_v1_api.list_namespaced_pod.return_value = list_pod_ret

        pool_info = self.manager.get_pool(fake_deployment_name)

        expected = {"total": 3, "available": 1}
        self.assertEqual(expected, pool_info)

    def test_get_pool_not_ready(self):
        fake_deployment_name = self.rand_name('deployment', prefix=self.prefix)

        ret = mock.Mock()
        ret.status.replicas = None
        self.k8s_v1_ext.read_namespaced_deployment.return_value = ret

        pool_info = self.manager.get_pool(fake_deployment_name)

        expected = {"total": 0, "available": 0}
        self.assertEqual(expected, pool_info)

    def test_prepare_execution_no_image(self):
        pod = mock.Mock()
        pod.metadata.name = self.rand_name('pod', prefix=self.prefix)
        pod.metadata.labels = {'pod1_key1': 'pod1_value1'}
        list_pod_ret = mock.Mock()
        list_pod_ret.items = [pod]
        self.k8s_v1_api.list_namespaced_pod.return_value = list_pod_ret
        self.k8s_v1_api.create_namespaced_service.return_value = (
            self._create_service()
        )
        self.k8s_v1_api.list_node.return_value = (
            self._create_nodes_with_external_ip()
        )
        runtime_id = common.generate_unicode_uuid()
        function_id = common.generate_unicode_uuid()

        pod_names, service_url = self.manager.prepare_execution(
            function_id, 0, rlimit=None, image=None, identifier=runtime_id,
            labels={'runtime_id': runtime_id})

        self.assertEqual(pod.metadata.name, pod_names)
        self.assertEqual(
            'http://%s:%s' % (SERVICE_ADDRESS_EXTERNAL, SERVICE_PORT),
            service_url)

        # in _choose_available_pods
        self.k8s_v1_api.list_namespaced_pod.assert_called_once_with(
            self.fake_namespace,
            label_selector='function_id=%s,function_version=0' % (function_id)
        )

        # in _prepare_pod -> _update_pod_label
        pod_labels = {
            'pod1_key1': 'pod1_value1',
            'function_id': function_id,
            'function_version': '0'
        }
        body = {'metadata': {'labels': pod_labels}}
        self.k8s_v1_api.patch_namespaced_pod.assert_called_once_with(
            pod.metadata.name, self.fake_namespace, body)

        # in _prepare_pod
        service_body = self.manager.service_template.render(
            {
                'service_name': 'service-%s-0' % function_id,
                'labels': {'function_id': function_id,
                           'function_version': '0',
                           'runtime_id': runtime_id},
                'selector': pod_labels
            }
        )
        self.k8s_v1_api.create_namespaced_service.assert_called_once_with(
            self.fake_namespace, yaml.safe_load(service_body))

    def test_prepare_execution_with_image(self):
        function_id = common.generate_unicode_uuid()
        image = self.rand_name('image', prefix=self.prefix)
        identifier = ('%s-%s' %
                      (common.generate_unicode_uuid(dashed=False), function_id)
                      )[:63]

        pod_name, url = self.manager.prepare_execution(
            function_id, 0, rlimit=self.rlimit, image=image,
            identifier=identifier)

        self.assertEqual(identifier, pod_name)
        self.assertIsNone(url)

        # in _create_pod
        pod_body = self.manager.pod_template.render(
            {
                'pod_name': identifier,
                'labels': {'function_id': function_id},
                'pod_image': image,
                'input': [],
                'req_cpu': str(cfg.CONF.resource_limits.default_cpu),
                'req_memory': str(cfg.CONF.resource_limits.default_memory),
                'limit_cpu': str(cfg.CONF.resource_limits.default_cpu),
                'limit_memory': str(cfg.CONF.resource_limits.default_memory)
            }
        )
        self.k8s_v1_api.create_namespaced_pod.assert_called_once_with(
            self.fake_namespace, body=yaml.safe_load(pod_body))

    def test_prepare_execution_with_image_function_input(self):
        function_id = common.generate_unicode_uuid()
        image = self.rand_name('image', prefix=self.prefix)
        identifier = ('%s-%s' % (
                      common.generate_unicode_uuid(dashed=False),
                      function_id)
                      )[:63]
        fake_input = {'__function_input': 'input_item1 input_item2'}

        pod_name, url = self.manager.prepare_execution(
            function_id, 0, rlimit=self.rlimit, image=image,
            identifier=identifier, input=fake_input)

        # in _create_pod
        pod_body = self.manager.pod_template.render(
            {
                'pod_name': identifier,
                'labels': {'function_id': function_id},
                'pod_image': image,
                'input': ['input_item1', 'input_item2'],
                'req_cpu': str(cfg.CONF.resource_limits.default_cpu),
                'req_memory': str(cfg.CONF.resource_limits.default_memory),
                'limit_cpu': str(cfg.CONF.resource_limits.default_cpu),
                'limit_memory': str(cfg.CONF.resource_limits.default_memory)
            }
        )
        self.k8s_v1_api.create_namespaced_pod.assert_called_once_with(
            self.fake_namespace, body=yaml.safe_load(pod_body))

    def test_prepare_execution_with_image_json_input(self):
        function_id = common.generate_unicode_uuid()
        image = self.rand_name('image', prefix=self.prefix)
        identifier = ('%s-%s' % (
                      common.generate_unicode_uuid(dashed=False),
                      function_id)
                      )[:63]
        fake_input = '["input_item3", "input_item4"]'

        pod_name, url = self.manager.prepare_execution(
            function_id, 0, rlimit=self.rlimit, image=image,
            identifier=identifier, input=fake_input)

        # in _create_pod
        pod_body = self.manager.pod_template.render(
            {
                'pod_name': identifier,
                'labels': {'function_id': function_id},
                'pod_image': image,
                'input': ['input_item3', 'input_item4'],
                'req_cpu': str(cfg.CONF.resource_limits.default_cpu),
                'req_memory': str(cfg.CONF.resource_limits.default_memory),
                'limit_cpu': str(cfg.CONF.resource_limits.default_cpu),
                'limit_memory': str(cfg.CONF.resource_limits.default_memory)
            }
        )
        self.k8s_v1_api.create_namespaced_pod.assert_called_once_with(
            self.fake_namespace, body=yaml.safe_load(pod_body))

    def test_prepare_execution_with_image_pod_failed(self):
        function_id = common.generate_unicode_uuid()
        image = self.rand_name('image', prefix=self.prefix)
        identifier = (
            '%s-%s' % (common.generate_unicode_uuid(dashed=True), function_id)
        )[:63]
        self.k8s_v1_api.create_namespaced_pod.side_effect = RuntimeError

        self.assertRaises(
            exc.OrchestratorException,
            self.manager.prepare_execution,
            function_id,
            0,
            rlimit=self.rlimit,
            image=image,
            identifier=identifier,
        )

    def test_prepare_execution_not_image_no_worker_available(self):
        ret_pods = mock.Mock()
        ret_pods.items = []
        self.k8s_v1_api.list_namespaced_pod.return_value = ret_pods
        function_id = common.generate_unicode_uuid()
        runtime_id = common.generate_unicode_uuid()
        labels = {'runtime_id': runtime_id}

        self.assertRaisesRegex(
            exc.OrchestratorException,
            "^Execution preparation failed\.$",
            self.manager.prepare_execution,
            function_id, 0, rlimit=None, image=None,
            identifier=runtime_id, labels=labels)

        # in _choose_available_pods
        list_calls = [
            mock.call(
                self.fake_namespace,
                label_selector=('function_id=%s,function_version=0' %
                                function_id)
            ),
            mock.call(
                self.fake_namespace,
                label_selector='!function_id,runtime_id=%s' % runtime_id
            )
        ]
        self.k8s_v1_api.list_namespaced_pod.assert_has_calls(list_calls)
        self.assertEqual(2, self.k8s_v1_api.list_namespaced_pod.call_count)

    def test_prepare_execution_service_already_exists(self):
        pod = mock.Mock()
        pod.metadata.name = self.rand_name('pod', prefix=self.prefix)
        pod.metadata.labels = {'pod1_key1': 'pod1_value1'}
        list_pod_ret = mock.Mock()
        list_pod_ret.items = [pod]
        self.k8s_v1_api.list_namespaced_pod.return_value = list_pod_ret
        exception = RuntimeError()
        exception.status = 409
        self.k8s_v1_api.create_namespaced_service.side_effect = exception
        self.k8s_v1_api.read_namespaced_service.return_value = (
            self._create_service()
        )
        self.k8s_v1_api.list_node.return_value = (
            self._create_nodes_with_external_ip()
        )
        runtime_id = common.generate_unicode_uuid()
        function_id = common.generate_unicode_uuid()

        pod_names, service_url = self.manager.prepare_execution(
            function_id, 0, rlimit=None, image=None, identifier=runtime_id,
            labels={'runtime_id': runtime_id})

        # in _prepare_pod
        self.k8s_v1_api.read_namespaced_service.assert_called_once_with(
            'service-%s-0' % function_id, self.fake_namespace)

    def test_prepare_execution_create_service_failed(self):
        pod = mock.Mock()
        pod.metadata.name = self.rand_name('pod', prefix=self.prefix)
        pod.metadata.labels = None
        ret_pods = mock.Mock()
        ret_pods.items = [pod]
        self.k8s_v1_api.list_namespaced_pod.return_value = ret_pods
        exception = RuntimeError()
        exception.status = 500
        self.k8s_v1_api.create_namespaced_service.side_effect = exception
        function_id = common.generate_unicode_uuid()
        runtime_id = common.generate_unicode_uuid()

        with mock.patch.object(
            self.manager, 'delete_function'
        ) as delete_function_mock:
            self.assertRaisesRegex(
                exc.OrchestratorException,
                '^Execution preparation failed\.$',
                self.manager.prepare_execution,
                function_id, 0, rlimit=None, image=None, identifier=runtime_id,
                labels={'runtime_id': runtime_id})

            delete_function_mock.assert_called_once_with(
                function_id,
                0,
                {
                    'runtime_id': runtime_id,
                    'function_id': function_id,
                    'function_version': '0'
                }
            )

    def test_prepare_execution_service_internal_ip(self):
        pod = mock.Mock()
        pod.metadata.name = self.rand_name('pod', prefix=self.prefix)
        pod.metadata.labels = {'pod1_key1': 'pod1_value1'}
        list_pod_ret = mock.Mock()
        list_pod_ret.items = [pod]
        self.k8s_v1_api.list_namespaced_pod.return_value = list_pod_ret
        self.k8s_v1_api.create_namespaced_service.return_value = (
            self._create_service()
        )
        self.k8s_v1_api.list_node.return_value = (
            self._create_nodes_with_internal_ip()
        )
        runtime_id = common.generate_unicode_uuid()
        function_id = common.generate_unicode_uuid()

        pod_names, service_url = self.manager.prepare_execution(
            function_id, 0, rlimit=None, image=None, identifier=runtime_id,
            labels={'runtime_id': runtime_id})

        self.assertEqual(pod.metadata.name, pod_names)
        self.assertEqual(
            'http://%s:%s' % (SERVICE_ADDRESS_INTERNAL, SERVICE_PORT),
            service_url)

    def test_run_execution_image_type_function(self):
        pod = mock.Mock()
        status = mock.Mock()
        status.state.terminated.finished_at = datetime.datetime(2018, 9, 4, 10,
                                                                1, 50)
        status.state.terminated.started_at = datetime.datetime(2018, 9, 4, 10,
                                                               1, 40)
        pod.status.phase = 'Succeeded'
        pod.status.container_statuses = [status]
        self.k8s_v1_api.read_namespaced_pod.return_value = pod
        fake_log = 'fake log'
        self.k8s_v1_api.read_namespaced_pod_log.return_value = fake_log
        execution_id = common.generate_unicode_uuid()
        function_id = common.generate_unicode_uuid()
        identifier = 'fake_identifier'

        result, output = self.manager.run_execution(execution_id, function_id,
                                                    0, identifier=identifier)

        self.k8s_v1_api.read_namespaced_pod.assert_called_once_with(
            identifier, self.fake_namespace)
        self.k8s_v1_api.read_namespaced_pod_log.assert_called_once_with(
            identifier, self.fake_namespace)
        self.assertTrue(result)

        expected_output = {'duration': 10, 'logs': fake_log}
        self.assertEqual(expected_output, output)

    def test_run_execution_image_type_function_retry(self):
        pod1 = mock.Mock()
        pod1.status.phase = ''
        pod2 = mock.Mock()
        status = mock.Mock()
        status.state.terminated.finished_at = datetime.datetime(2018, 9, 4, 10,
                                                                1, 50)
        status.state.terminated.started_at = datetime.datetime(2018, 9, 4, 10,
                                                               1, 40)
        pod2.status.phase = 'Succeeded'
        pod2.status.container_statuses = [status]
        self.k8s_v1_api.read_namespaced_pod.side_effect = [pod1, pod2]
        fake_log = 'fake log'
        self.k8s_v1_api.read_namespaced_pod_log.return_value = fake_log
        execution_id = common.generate_unicode_uuid()
        function_id = common.generate_unicode_uuid()

        result, output = self.manager.run_execution(execution_id, function_id,
                                                    0, timeout=5)

        self.assertEqual(2, self.k8s_v1_api.read_namespaced_pod.call_count)
        self.k8s_v1_api.read_namespaced_pod_log.assert_called_once_with(
            None, self.fake_namespace)
        self.assertTrue(result)

        expected_output = {'duration': 10, 'logs': fake_log}
        self.assertEqual(expected_output, output)

    def test_run_execution_image_type_function_timeout(self):
        execution_id = common.generate_unicode_uuid()
        function_id = common.generate_unicode_uuid()
        pod1 = mock.Mock()
        pod1.status.phase = ''
        self.k8s_v1_api.read_namespaced_pod.return_value = pod1

        result, output = self.manager.run_execution(
            execution_id, function_id, 0,
            identifier='fake_identifier',
            timeout=1
        )

        self.assertFalse(result)

        expected_output = {
            'output': 'Function execution timeout.',
            'duration': 1
        }
        self.assertEqual(expected_output, output)

    def test_run_execution_image_type_function_read_pod_exception(self):
        self.k8s_v1_api.read_namespaced_pod.side_effect = RuntimeError
        execution_id = common.generate_unicode_uuid()
        function_id = common.generate_unicode_uuid()

        result, output = self.manager.run_execution(execution_id, function_id,
                                                    0, timeout=5)

        self.k8s_v1_api.read_namespaced_pod.assert_called_once_with(
            None, self.fake_namespace)
        self.k8s_v1_api.read_namespaced_pod_log.assert_not_called()
        self.assertFalse(result)

        expected_output = {
            'output': 'Function execution failed.',
            'duration': 0
        }
        self.assertEqual(expected_output, output)

    @mock.patch('qinling.engine.utils.url_request')
    def test_run_execution_version_0(self, mock_request):
        mock_request.return_value = (True, 'fake output')
        execution_id = common.generate_unicode_uuid()
        function_id = common.generate_unicode_uuid()
        timeout = 3

        result, output = self.manager.run_execution(
            execution_id, function_id, 0, rlimit=self.rlimit,
            service_url='FAKE_URL', timeout=timeout
        )

        download_url = ('http://127.0.0.1:7070/v1/functions/%s?download=true'
                        % function_id)
        data = {
            'execution_id': execution_id,
            'cpu': self.rlimit['cpu'],
            'memory_size': self.rlimit['memory_size'],
            'input': None,
            'function_id': function_id,
            'function_version': 0,
            'entry': 'main.main',
            'download_url': download_url,
            'request_id': self.ctx.request_id,
            'timeout': timeout,
        }

        mock_request.assert_called_once_with(
            self.manager.session, 'FAKE_URL/execute', body=data
        )

    def test_delete_function(self):
        # Deleting namespaced service is also tested in this.
        svc1 = mock.Mock()
        svc1_name = self.rand_name('service', prefix=self.prefix)
        svc1.metadata.name = svc1_name
        svc2 = mock.Mock()
        svc2_name = self.rand_name('service', prefix=self.prefix)
        svc2.metadata.name = svc2_name
        services = mock.Mock()
        services.items = [svc1, svc2]
        self.k8s_v1_api.list_namespaced_service.return_value = services
        function_id = common.generate_unicode_uuid()

        self.manager.delete_function(function_id, 0)

        args, kwargs = self.k8s_v1_api.list_namespaced_service.call_args
        self.assertIn(self.fake_namespace, args)
        self.assertIn(
            "function_id=%s" % function_id,
            kwargs.get("label_selector")
        )
        self.assertIn(
            "function_version=0",
            kwargs.get("label_selector")
        )

        delete_service_calls = [
            mock.call(svc1_name, self.fake_namespace),
            mock.call(svc2_name, self.fake_namespace)
        ]
        self.k8s_v1_api.delete_namespaced_service.assert_has_calls(
            delete_service_calls)
        self.assertEqual(
            2, self.k8s_v1_api.delete_namespaced_service.call_count
        )

        args, kwargs = self.k8s_v1_api.delete_collection_namespaced_pod. \
            call_args
        self.assertIn(self.fake_namespace, args)
        self.assertIn(
            "function_id=%s" % function_id,
            kwargs.get("label_selector")
        )
        self.assertIn(
            "function_version=0",
            kwargs.get("label_selector")
        )

    def test_delete_function_with_labels(self):
        services = mock.Mock()
        services.items = []
        labels = {'key1': 'value1', 'key2': 'value2'}
        selector = common.convert_dict_to_string(labels)
        self.k8s_v1_api.list_namespaced_service.return_value = services
        function_id = common.generate_unicode_uuid()

        self.manager.delete_function(function_id, 0, labels=labels)

        self.k8s_v1_api.list_namespaced_service.assert_called_once_with(
            self.fake_namespace, label_selector=selector)
        self.k8s_v1_api.delete_namespaced_service.assert_not_called()
        delete_pod = self.k8s_v1_api.delete_collection_namespaced_pod
        delete_pod.assert_called_once_with(
            self.fake_namespace, label_selector=selector)

    def test_scaleup_function(self):
        pod = mock.Mock()
        pod.metadata.name = self.rand_name('pod', prefix=self.prefix)
        pod.metadata.labels = {'pod1_key1': 'pod1_value1'}
        list_pod_ret = mock.Mock()
        list_pod_ret.items = [pod]
        self.k8s_v1_api.list_namespaced_pod.return_value = list_pod_ret
        self.k8s_v1_api.create_namespaced_service.return_value = (
            self._create_service()
        )
        self.k8s_v1_api.list_node.return_value = (
            self._create_nodes_with_external_ip()
        )
        runtime_id = common.generate_unicode_uuid()
        function_id = common.generate_unicode_uuid()

        pod_names, service_url = self.manager.scaleup_function(
            function_id, 0, identifier=runtime_id
        )

        self.assertEqual([pod.metadata.name], pod_names)
        self.assertEqual(
            'http://%s:%s' % (SERVICE_ADDRESS_EXTERNAL, SERVICE_PORT),
            service_url)

        # in _choose_available_pods
        self.k8s_v1_api.list_namespaced_pod.assert_called_once_with(
            self.fake_namespace,
            label_selector='!function_id,runtime_id=%s' % runtime_id)

        # in _prepare_pod -> _update_pod_label
        pod_labels = {
            'pod1_key1': 'pod1_value1',
            'function_id': function_id,
            'function_version': '0'
        }
        body = {'metadata': {'labels': pod_labels}}
        self.k8s_v1_api.patch_namespaced_pod.assert_called_once_with(
            pod.metadata.name, self.fake_namespace, body)

        # in _prepare_pod
        service_body = self.manager.service_template.render(
            {
                'service_name': 'service-%s-0' % function_id,
                'labels': {'function_id': function_id,
                           'function_version': 0,
                           'runtime_id': runtime_id},
                'selector': pod_labels
            }
        )
        self.k8s_v1_api.create_namespaced_service.assert_called_once_with(
            self.fake_namespace, yaml.safe_load(service_body))

    def test_scaleup_function_not_enough_workers(self):
        runtime_id = common.generate_unicode_uuid()
        function_id = common.generate_unicode_uuid()
        ret_pods = mock.Mock()
        ret_pods.items = [mock.Mock()]
        self.k8s_v1_api.list_namespaced_pod.return_value = ret_pods

        self.assertRaisesRegex(
            exc.OrchestratorException,
            "^Not enough workers available\.$",
            self.manager.scaleup_function,
            function_id, 0, identifier=runtime_id, count=2)

    def test_scaleup_function_service_already_exists(self):
        pod = mock.Mock()
        pod.metadata.name = self.rand_name('pod', prefix=self.prefix)
        pod.metadata.labels = {'pod1_key1': 'pod1_value1'}
        list_pod_ret = mock.Mock()
        list_pod_ret.items = [pod]
        self.k8s_v1_api.list_namespaced_pod.return_value = list_pod_ret
        exception = RuntimeError()
        exception.status = 409
        self.k8s_v1_api.create_namespaced_service.side_effect = exception
        self.k8s_v1_api.read_namespaced_service.return_value = (
            self._create_service()
        )
        self.k8s_v1_api.list_node.return_value = (
            self._create_nodes_with_external_ip()
        )
        runtime_id = common.generate_unicode_uuid()
        function_id = common.generate_unicode_uuid()

        pod_names, service_url = self.manager.scaleup_function(
            function_id, 0, identifier=runtime_id)

        # in _prepare_pod
        self.k8s_v1_api.read_namespaced_service.assert_called_once_with(
            'service-%s-0' % function_id, self.fake_namespace)

    def test_scaleup_function_service_create_failed(self):
        pod = mock.Mock()
        pod.metadata.name = self.rand_name('pod', prefix=self.prefix)
        pod.metadata.labels = None
        list_pod_ret = mock.Mock()
        list_pod_ret.items = [pod]
        self.k8s_v1_api.list_namespaced_pod.return_value = list_pod_ret
        exception = RuntimeError()
        exception.status = 500
        self.k8s_v1_api.create_namespaced_service.side_effect = exception
        runtime_id = common.generate_unicode_uuid()
        function_id = common.generate_unicode_uuid()

        self.assertRaises(
            RuntimeError,
            self.manager.scaleup_function,
            function_id, 0, identifier=runtime_id)

    def test_scaleup_function_service_internal_ip(self):
        pod = mock.Mock()
        pod.metadata.name = self.rand_name('pod', prefix=self.prefix)
        pod.metadata.labels = None
        list_pod_ret = mock.Mock()
        list_pod_ret.items = [pod]
        self.k8s_v1_api.list_namespaced_pod.return_value = list_pod_ret
        self.k8s_v1_api.create_namespaced_service.return_value = (
            self._create_service()
        )
        self.k8s_v1_api.list_node.return_value = (
            self._create_nodes_with_internal_ip()
        )
        runtime_id = common.generate_unicode_uuid()
        function_id = common.generate_unicode_uuid()

        pod_names, service_url = self.manager.scaleup_function(
            function_id, 0, identifier=runtime_id)

        self.assertEqual([pod.metadata.name], pod_names)
        self.assertEqual(
            'http://%s:%s' % (SERVICE_ADDRESS_INTERNAL, SERVICE_PORT),
            service_url)

    def test_delete_worker(self):
        pod_name = self.rand_name('pod', prefix=self.prefix)

        self.manager.delete_worker(pod_name)

        self.k8s_v1_api.delete_namespaced_pod.assert_called_once_with(
            pod_name, self.fake_namespace
        )
