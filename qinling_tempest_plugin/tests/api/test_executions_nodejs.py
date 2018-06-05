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
from tempest import config
from tempest.lib import decorators

from qinling_tempest_plugin.tests import base

CONF = config.CONF


class NodeJSExecutionsTest(base.BaseQinlingTest):
    name_prefix = 'NodeJSExecutionsTest'
    image = CONF.qinling.nodejs_runtime_image

    def setUp(self):
        super(NodeJSExecutionsTest, self).setUp()
        self.wait_runtime_available(self.runtime_id)

    @decorators.idempotent_id('e3046fa4-2289-11e8-b720-00224d6b7bc1')
    def test_basic_nodejs_execution(self):
        package = self.create_package(name='nodejs/test_nodejs_basic.js')
        function_id = self.create_function(package_path=package)
        resp, body = self.client.create_execution(function_id,
                                                  input='{"name": "Qinling"}')
        self.assertEqual(201, resp.status)
        execution_id = body['id']
        self.addCleanup(self.client.delete_resource, 'executions',
                        execution_id, ignore_notfound=True)
        self.assertEqual('success', body['status'])
