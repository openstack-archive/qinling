# Copyright 2018 Catalyst IT Ltd
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
import pkg_resources
import tempfile
import zipfile

import requests
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators

from qinling_tempest_plugin.tests import base


class WebhooksTest(base.BaseQinlingTest):
    name_prefix = 'WebhooksTest'

    @classmethod
    def resource_setup(cls):
        super(WebhooksTest, cls).resource_setup()

        cls.runtime_id = None

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

        super(WebhooksTest, cls).resource_cleanup()

    def setUp(self):
        super(WebhooksTest, self).setUp()
        self.await_runtime_available(self.runtime_id)
        self._create_function()

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

    @decorators.idempotent_id('37DCD022-32D6-48D1-B90C-31D605DBE53B')
    def test_webhook_invoke(self):
        webhook_id, url = self.create_webhook()
        resp = requests.post(url, data={'name': 'qinling'}, verify=False)
        self.assertEqual(202, resp.status_code)
        resp_exec_id = resp.json().get('execution_id')
        self.addCleanup(self.client.delete_resource, 'executions',
                        resp_exec_id, ignore_notfound=True)

        resp, body = self.client.get_resources(
            'executions',
            {'description': 'has:%s' % webhook_id}
        )
        self.assertEqual(200, resp.status)
        self.assertEqual(1, len(body['executions']))
        exec_id = body['executions'][0]['id']
        self.assertEqual(resp_exec_id, exec_id)
        self.await_execution_success(exec_id)

        resp, body = self.client.get_execution_log(exec_id)
        self.assertEqual(200, resp.status)
        self.assertIn('qinling', body)
