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
import tempfile
import zipfile

from tempest.lib.common.utils import data_utils
from tempest.lib import decorators

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

        # Wait until runtime is available
        self.await_runtime_available(self.runtime_id)

        python_file_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                os.pardir,
                os.pardir,
                'functions/python_test.py'
            )
        )
        base_name, extention = os.path.splitext(python_file_path)
        self.base_name = os.path.basename(base_name)
        self.python_zip_file = os.path.join(
            tempfile.gettempdir(),
            '%s.zip' % self.base_name
        )

        if not os.path.isfile(self.python_zip_file):
            zf = zipfile.ZipFile(self.python_zip_file, mode='w')
            try:
                # Use default compression mode, may change in future.
                zf.write(
                    python_file_path,
                    '%s%s' % (self.base_name, extention),
                    compress_type=zipfile.ZIP_STORED
                )
            finally:
                zf.close()

        # Create function
        function_name = data_utils.rand_name('function',
                                             prefix=self.name_prefix)
        with open(self.python_zip_file, 'rb') as package_data:
            resp, body = self.client.create_function(
                {"source": "package"},
                self.runtime_id,
                name=function_name,
                package_data=package_data,
                entry='%s.main' % self.base_name
            )
            self.function_id = body['id']

        self.addCleanup(self.client.delete_resource, 'functions',
                        self.function_id, ignore_notfound=True)

    @decorators.idempotent_id('2a93fab0-2dae-4748-b0d4-f06b735ff451')
    def test_create_list_get_delete_execution(self):
        resp, body = self.client.create_execution(self.function_id,
                                                  input={'name': 'Qinling'})

        self.assertEqual(201, resp.status)
        self.assertEqual('success', body['status'])

        execution_id = body['id']
        self.addCleanup(self.client.delete_resource, 'executions',
                        execution_id, ignore_notfound=True)

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

    @decorators.idempotent_id('8096cc52-64d2-4660-a657-9ac0bdd743ae')
    def test_execution_async(self):
        resp, body = self.client.create_execution(self.function_id, sync=False)

        self.assertEqual(201, resp.status)
        self.assertEqual('running', body['status'])

        execution_id = body['id']
        self.addCleanup(self.client.delete_resource, 'executions',
                        execution_id, ignore_notfound=True)

        self.await_execution_success(execution_id)

    @decorators.idempotent_id('6cb47b1d-a8c6-48f2-a92f-c4f613c33d1c')
    def test_execution_log(self):
        resp, body = self.client.create_execution(self.function_id,
                                                  input={'name': 'OpenStack'})

        self.assertEqual(201, resp.status)
        self.assertEqual('success', body['status'])

        execution_id = body['id']
        self.addCleanup(self.client.delete_resource, 'executions',
                        execution_id, ignore_notfound=True)

        # Get execution log
        resp, body = self.client.get_execution_log(execution_id)

        self.assertEqual(200, resp.status)
        self.assertIn('Hello, OpenStack', body)
