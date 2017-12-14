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
from concurrent import futures
import os
import pkg_resources
import tempfile
import zipfile

import futurist
from oslo_serialization import jsonutils
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions

from qinling_tempest_plugin.tests import base


# TODO(kong): Be careful that for k8s cluster, the default pool size is 3,
# maybe we need customize that in future if there are many test cases but with
# insufficient pods.
class ExecutionsTest(base.BaseQinlingTest):
    name_prefix = 'ExecutionsTest'

    @classmethod
    def resource_setup(cls):
        super(ExecutionsTest, cls).resource_setup()

        cls.runtime_id = None

        # Create runtime for execution tests
        name = data_utils.rand_name('runtime', prefix=cls.name_prefix)
        _, body = cls.admin_client.create_runtime(
            'openstackqinling/python-runtime', name
        )
        cls.runtime_id = body['id']

    @classmethod
    def resource_cleanup(cls):
        if cls.runtime_id:
            cls.admin_client.delete_resource('runtimes', cls.runtime_id,
                                             ignore_notfound=True)

        super(ExecutionsTest, cls).resource_cleanup()

    def setUp(self):
        super(ExecutionsTest, self).setUp()
        self.await_runtime_available(self.runtime_id)

    def _create_function(self, name='python_test.py'):
        python_file_path = pkg_resources.resource_filename(
            'qinling_tempest_plugin',
            "functions/%s" % name
        )
        base_name, extention = os.path.splitext(python_file_path)
        module_name = os.path.basename(base_name)
        self.python_zip_file = os.path.join(
            tempfile.gettempdir(),
            '%s.zip' % module_name
        )

        if not os.path.isfile(self.python_zip_file):
            zf = zipfile.ZipFile(self.python_zip_file, mode='w')
            try:
                # Use default compression mode, may change in future.
                zf.write(
                    python_file_path,
                    '%s%s' % (module_name, extention),
                    compress_type=zipfile.ZIP_STORED
                )
            finally:
                zf.close()

        self.function_id = self.create_function(self.python_zip_file)

    @decorators.idempotent_id('2a93fab0-2dae-4748-b0d4-f06b735ff451')
    def test_crud_execution(self):
        self._create_function()

        resp, body = self.client.create_execution(self.function_id,
                                                  input={'name': 'Qinling'})

        self.assertEqual(201, resp.status)

        execution_id = body['id']
        self.addCleanup(self.client.delete_resource, 'executions',
                        execution_id, ignore_notfound=True)

        self.assertEqual('success', body['status'])

        # Get executions
        resp, body = self.client.get_resources('executions')

        self.assertEqual(200, resp.status)
        self.assertIn(
            execution_id,
            [execution['id'] for execution in body['executions']]
        )

        # Delete execution
        resp = self.client.delete_resource('executions', execution_id)

        self.assertEqual(204, resp.status)

    @decorators.idempotent_id('2199d1e6-de7d-4345-8745-a8184d6022b1')
    def test_get_all_admin(self):
        """Admin user can get executions of other projects"""
        self._create_function()

        resp, body = self.client.create_execution(self.function_id,
                                                  input={'name': 'Qinling'})
        self.assertEqual(201, resp.status)

        execution_id = body['id']
        self.addCleanup(self.client.delete_resource, 'executions',
                        execution_id, ignore_notfound=True)

        resp, body = self.admin_client.get_resources(
            'executions?all_projects=true'
        )
        self.assertEqual(200, resp.status)
        self.assertIn(
            execution_id,
            [execution['id'] for execution in body['executions']]
        )

    @decorators.idempotent_id('009fba47-957e-4de5-82e8-a032386d3ac0')
    def test_get_all_not_allowed(self):
        # Get other projects functions by normal user
        context = self.assertRaises(
            exceptions.Forbidden,
            self.client.get_resources,
            'executions?all_projects=true'
        )
        self.assertIn(
            'Operation not allowed',
            context.resp_body.get('faultstring')
        )

    @decorators.idempotent_id('8096cc52-64d2-4660-a657-9ac0bdd743ae')
    def test_execution_async(self):
        self._create_function()

        resp, body = self.client.create_execution(self.function_id, sync=False)

        self.assertEqual(201, resp.status)

        execution_id = body['id']
        self.addCleanup(self.client.delete_resource, 'executions',
                        execution_id, ignore_notfound=True)

        self.assertEqual('running', body['status'])

        self.await_execution_success(execution_id)

    @decorators.idempotent_id('6cb47b1d-a8c6-48f2-a92f-c4f613c33d1c')
    def test_execution_log(self):
        self._create_function()

        resp, body = self.client.create_execution(self.function_id,
                                                  input={'name': 'OpenStack'})

        self.assertEqual(201, resp.status)
        self.addCleanup(self.client.delete_resource, 'executions',
                        body['id'], ignore_notfound=True)
        self.assertEqual('success', body['status'])

        execution_id = body['id']

        # Get execution log
        resp, body = self.client.get_execution_log(execution_id)

        self.assertEqual(200, resp.status)
        self.assertIn('Hello, OpenStack', body)

    @decorators.idempotent_id('f22097dc-37db-484d-83d3-3a97e72ec576')
    def test_execution_concurrency_no_scale(self):
        self._create_function(name='test_python_sleep.py')

        def _create_execution():
            resp, body = self.client.create_execution(self.function_id)
            return resp, body

        futs = []
        with futurist.ThreadPoolExecutor(max_workers=10) as executor:
            for _ in range(3):
                fut = executor.submit(_create_execution)
                futs.append(fut)
            for f in futures.as_completed(futs):
                # Wait until we get the response
                resp, body = f.result()

                self.assertEqual(201, resp.status)
                self.addCleanup(self.client.delete_resource, 'executions',
                                body['id'], ignore_notfound=True)
                self.assertEqual('success', body['status'])

        resp, body = self.admin_client.get_function_workers(self.function_id)

        self.assertEqual(200, resp.status)
        self.assertEqual(1, len(body['workers']))

    @decorators.idempotent_id('a5ed173a-19b7-4c92-ac78-c8862ad1d1d2')
    def test_execution_concurrency_scale_up(self):
        self.await_runtime_available(self.runtime_id)
        self._create_function(name='test_python_sleep.py')

        def _create_execution():
            resp, body = self.client.create_execution(self.function_id)
            return resp, body

        futs = []
        with futurist.ThreadPoolExecutor(max_workers=10) as executor:
            for _ in range(6):
                fut = executor.submit(_create_execution)
                futs.append(fut)
            for f in futures.as_completed(futs):
                # Wait until we get the response
                resp, body = f.result()

                self.assertEqual(201, resp.status)
                self.addCleanup(self.client.delete_resource, 'executions',
                                body['id'], ignore_notfound=True)
                self.assertEqual('success', body['status'])

        resp, body = self.admin_client.get_function_workers(self.function_id)
        self.assertEqual(200, resp.status)
        self.assertEqual(2, len(body['workers']))

    @decorators.idempotent_id('a948382a-84af-4f0e-ad08-4297345e302c')
    def test_python_execution_file_limit(self):
        self._create_function(name='test_python_file_limit.py')

        resp, body = self.client.create_execution(self.function_id)

        self.assertEqual(201, resp.status)
        self.addCleanup(self.client.delete_resource, 'executions',
                        body['id'], ignore_notfound=True)
        self.assertEqual('failed', body['status'])

        output = jsonutils.loads(body['output'])
        self.assertIn(
            'Too many open files', output['output']
        )

    @decorators.idempotent_id('bf6f8f35-fa88-469b-8878-7aa85a8ce5ab')
    def test_python_execution_process_number(self):
        self._create_function(name='test_python_process_limit.py')

        resp, body = self.client.create_execution(self.function_id)

        self.assertEqual(201, resp.status)
        self.addCleanup(self.client.delete_resource, 'executions',
                        body['id'], ignore_notfound=True)
        self.assertEqual('failed', body['status'])

        output = jsonutils.loads(body['output'])
        self.assertIn(
            'too much resource consumption', output['output']
        )
