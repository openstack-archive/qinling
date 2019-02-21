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
import hashlib
import json
import requests

import futurist
from oslo_serialization import jsonutils
from tempest import config
from tempest.lib import decorators
from tempest.lib import exceptions
import testtools

from qinling_tempest_plugin.tests import base

CONF = config.CONF
INVOKE_ERROR = "Function execution failed because of too much resource " \
               "consumption"


class ExecutionsTest(base.BaseQinlingTest):
    name_prefix = 'ExecutionsTest'

    def setUp(self):
        super(ExecutionsTest, self).setUp()
        self.wait_runtime_available(self.runtime_id)

    @decorators.idempotent_id('2a93fab0-2dae-4748-b0d4-f06b735ff451')
    def test_crud_execution(self):
        function_id = self.create_function()
        resp, body = self.client.create_execution(function_id,
                                                  input='{"name": "Qinling"}')
        self.assertEqual(201, resp.status)
        execution_id_1 = body['id']
        self.addCleanup(self.client.delete_resource, 'executions',
                        execution_id_1, ignore_notfound=True)
        self.assertEqual('success', body['status'])

        # Create another execution without input
        resp, body = self.client.create_execution(function_id)
        self.assertEqual(201, resp.status)
        execution_id_2 = body['id']
        self.addCleanup(self.client.delete_resource, 'executions',
                        execution_id_2, ignore_notfound=True)
        self.assertEqual('success', body['status'])

        # Get executions
        resp, body = self.client.get_resources('executions')
        self.assertEqual(200, resp.status)
        expected = {execution_id_1, execution_id_2}
        actual = set([execution['id'] for execution in body['executions']])
        self.assertTrue(expected.issubset(actual))

        # Delete executions
        resp = self.client.delete_resource('executions', execution_id_1)
        self.assertEqual(204, resp.status)
        resp = self.client.delete_resource('executions', execution_id_2)
        self.assertEqual(204, resp.status)

    # @decorators.idempotent_id('6a388918-86eb-4e10-88e2-0032a7df38e9')
    # def test_create_execution_worker_lock_failed(self):
    #     """test_create_execution_worker_lock_failed
    #
    #     When creating an execution, the qinling-engine will check the load
    #     and try to scaleup the function if needed. A lock is required when
    #     doing this check.
    #
    #     In this test we acquire the lock manually, so that qinling will fail
    #     to acquire the lock.
    #     """
    #     function_id = self.create_function()
    #
    #     from qinling_tempest_plugin.tests import utils
    #     etcd3_client = utils.get_etcd_client()
    #     lock_id = "function_worker_%s_%s" % (function_id, 0)
    #     with etcd3_client.lock(id=lock_id):
    #         resp, body = self.client.create_execution(
    #             function_id, input='{"name": "Qinling"}'
    #         )
    #
    #     self.assertEqual(201, resp.status)
    #     self.assertEqual('error', body['status'])
    #     result = jsonutils.loads(body['result'])
    #     self.assertEqual('Function execution failed.', result['output'])

    @decorators.idempotent_id('2199d1e6-de7d-4345-8745-a8184d6022b1')
    def test_get_all_admin(self):
        """Admin user can get executions of other projects"""
        function_id = self.create_function()
        resp, body = self.client.create_execution(
            function_id, input='{"name": "Qinling"}'
        )
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

    @decorators.idempotent_id('794cdfb2-0a27-4e56-86e8-be18eee9400f')
    def test_create_with_function_version(self):
        function_id = self.create_function()
        execution_id = self.create_execution(function_id)
        resp, body = self.client.get_execution_log(execution_id)
        self.assertEqual(200, resp.status)
        self.assertIn('Hello, World', body)

        version_1 = self.create_function_version(function_id)
        execution_id = self.create_execution(function_id, version=version_1)
        resp, body = self.client.get_execution_log(execution_id)
        self.assertEqual(200, resp.status)
        self.assertIn('Hello, World', body)

        self.update_function_package(function_id,
                                     "python/test_python_sleep.py")
        version_2 = self.create_function_version(function_id)
        execution_id = self.create_execution(function_id, version=version_2)
        resp, body = self.client.get_execution_log(execution_id)
        self.assertEqual(200, resp.status)
        self.assertNotIn('Hello, World', body)

    @decorators.idempotent_id('dbf4bd84-bde3-4d1d-8dec-93aaf18b4b5f')
    def test_create_with_function_alias(self):
        function_id = self.create_function()

        alias_name = self.create_function_alias(function_id)
        execution_id = self.create_execution(alias_name=alias_name)
        resp, body = self.client.get_execution_log(execution_id)
        self.assertEqual(200, resp.status)
        self.assertIn('Hello, World', body)

        version_1 = self.create_function_version(function_id)
        alias_name_1 = self.create_function_alias(function_id, version_1)
        execution_id = self.create_execution(alias_name=alias_name_1)
        resp, body = self.client.get_execution_log(execution_id)
        self.assertEqual(200, resp.status)
        self.assertIn('Hello, World', body)

        self.update_function_package(function_id,
                                     "python/test_python_sleep.py")
        version_2 = self.create_function_version(function_id)
        alias_name_2 = self.create_function_alias(function_id, version_2)
        execution_id = self.create_execution(alias_name=alias_name_2)
        resp, body = self.client.get_execution_log(execution_id)
        self.assertEqual(200, resp.status)
        self.assertNotIn('Hello, World', body)

    @decorators.idempotent_id('8096cc52-64d2-4660-a657-9ac0bdd743ae')
    def test_execution_async(self):
        function_id = self.create_function()
        resp, body = self.client.create_execution(function_id, sync=False)
        self.assertEqual(201, resp.status)

        execution_id = body['id']
        self.addCleanup(self.client.delete_resource, 'executions',
                        execution_id, ignore_notfound=True)

        self.assertEqual('running', body['status'])
        self.wait_execution_success(execution_id)

    @decorators.idempotent_id('6cb47b1d-a8c6-48f2-a92f-c4f613c33d1c')
    def test_execution_log(self):
        function_id = self.create_function()
        resp, body = self.client.create_execution(
            function_id, input='{"name": "OpenStack"}'
        )

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
        package = self.create_package(name='python/test_python_sleep.py')
        function_id = self.create_function(package_path=package)

        def _create_execution():
            resp, body = self.client.create_execution(function_id)
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

        resp, body = self.admin_client.get_function_workers(function_id)

        self.assertEqual(200, resp.status)
        self.assertEqual(1, len(body['workers']))

    @decorators.idempotent_id('a5ed173a-19b7-4c92-ac78-c8862ad1d1d2')
    def test_execution_concurrency_scale_up(self):
        package = self.create_package(name='python/test_python_sleep.py')
        function_id = self.create_function(package_path=package)

        def _create_execution():
            resp, body = self.client.create_execution(function_id)
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

        resp, body = self.admin_client.get_function_workers(function_id)
        self.assertEqual(200, resp.status)
        self.assertEqual(2, len(body['workers']))

    @decorators.idempotent_id('d0598868-e45d-11e7-9125-00224d6b7bc1')
    def test_image_function_execution(self):
        function_id = self.create_function(
            image="openstackqinling/alpine-test")
        resp, body = self.client.create_execution(function_id,
                                                  input='Qinling')

        self.assertEqual(201, resp.status)
        execution_id = body['id']
        self.addCleanup(self.client.delete_resource, 'executions',
                        execution_id, ignore_notfound=True)

        self.assertEqual('success', body['status'])
        self.assertIn('duration', jsonutils.loads(body['result']))

        resp, body = self.client.get_execution_log(execution_id)
        self.assertEqual(200, resp.status)
        self.assertIn('Qinling', body)

    @decorators.idempotent_id('ab962144-d5b1-11e8-978f-026f8338c1e5')
    def test_image_function_execution_timeout(self):
        function_id = self.create_function(image="lingxiankong/sleep")
        resp, body = self.client.create_execution(function_id,
                                                  input='6')

        self.assertEqual(201, resp.status)
        self.addCleanup(self.client.delete_resource, 'executions',
                        body['id'], ignore_notfound=True)
        self.assertEqual('failed', body['status'])

        result = jsonutils.loads(body['result'])

        self.assertGreaterEqual(result['duration'], 5)
        self.assertIn(
            'Function execution timeout', result['output']
        )

        # Update function timeout
        resp, _ = self.client.update_function(
            function_id,
            timeout=15
        )
        self.assertEqual(200, resp.status_code)

        resp, body = self.client.create_execution(function_id,
                                                  input='6')

        self.assertEqual(201, resp.status)
        self.addCleanup(self.client.delete_resource, 'executions',
                        body['id'], ignore_notfound=True)
        self.assertEqual('success', body['status'])

        result = jsonutils.loads(body['result'])
        self.assertGreaterEqual(result['duration'], 6)

    @decorators.idempotent_id('ccfe67ce-e467-11e7-916c-00224d6b7bc1')
    def test_python_execution_positional_args(self):
        package = self.create_package(
            name='python/test_python_positional_args.py'
        )
        function_id = self.create_function(package_path=package)

        resp, body = self.client.create_execution(function_id,
                                                  input='Qinling')

        self.assertEqual(201, resp.status)
        self.addCleanup(self.client.delete_resource, 'executions',
                        body['id'], ignore_notfound=True)
        self.assertEqual('success', body['status'])

        result = jsonutils.loads(body['result'])
        self.assertIn('Qinling', result['output'])

    @decorators.idempotent_id('a948382a-84af-4f0e-ad08-4297345e302c')
    def test_python_execution_file_limit(self):
        package = self.create_package(name='python/test_python_file_limit.py')
        function_id = self.create_function(package_path=package)

        resp, body = self.client.create_execution(function_id)

        self.assertEqual(201, resp.status)
        self.addCleanup(self.client.delete_resource, 'executions',
                        body['id'], ignore_notfound=True)
        self.assertEqual('failed', body['status'])

        result = jsonutils.loads(body['result'])
        self.assertIn(
            'Too many open files', result['output']
        )

    @decorators.idempotent_id('bf6f8f35-fa88-469b-8878-7aa85a8ce5ab')
    def test_python_execution_process_number(self):
        package = self.create_package(
            name='python/test_python_process_limit.py'
        )
        function_id = self.create_function(package_path=package)

        resp, body = self.client.create_execution(function_id)

        self.assertEqual(201, resp.status)
        self.addCleanup(self.client.delete_resource, 'executions',
                        body['id'], ignore_notfound=True)
        self.assertEqual('failed', body['status'])

        result = jsonutils.loads(body['result'])
        self.assertIn(
            'too much resource consumption', result['output']
        )

    @decorators.idempotent_id('2b5f0787-b82d-4fc4-af76-cf86d389a76b')
    def test_python_execution_memory_limit(self):
        """In this case, the following steps are taken:

        1. Create a function that requires ~80M memory to run.
        2. Create an execution using the function.
        3. Verify that the execution is killed by the OOM-killer
           because the function memory limit is only 32M(default).
        4. Increase the function memory limit to 96M.
        5. Create another execution.
        6. Check the execution finished normally.
        """

        # Create function
        package = self.create_package(
            name='python/test_python_memory_limit.py'
        )
        function_id = self.create_function(package_path=package)

        # Invoke function
        resp, body = self.client.create_execution(function_id)

        execution_id = body['id']
        self.addCleanup(self.client.delete_resource, 'executions',
                        execution_id, ignore_notfound=True)

        # Check the process is killed
        self.assertEqual(201, resp.status)
        result = json.loads(body['result'])
        output = result.get('output')
        self.assertEqual(INVOKE_ERROR, output)

        # Increase the memory limit to 100663296(96M).
        resp, body = self.client.update_function(
            function_id, memory_size=100663296)
        self.assertEqual(200, resp.status_code)

        # Invoke the function again
        resp, body = self.client.create_execution(function_id)

        execution_id = body['id']
        self.addCleanup(self.client.delete_resource, 'executions',
                        execution_id, ignore_notfound=True)

        # Check the process exited normally
        self.assertEqual(201, resp.status)
        result = json.loads(body['result'])
        output = result.get('output')
        # The function returns the length of a list containing 4 long strings.
        self.assertEqual(4, output)

    @decorators.idempotent_id('ed714f98-29fe-4e8d-b6ee-9730f92bddea')
    def test_python_execution_cpu_limit(self):
        """In this case, the following steps are taken:

        1. Create a function that takes some time to finish (calculating the
           first 50000 digits of PI)
        2. Create an execution using the function.
        3. Store the duration of the first execution.
        4. Increase the function cpu limit from 100(default) to 200 millicpu.
        5. Create another execution.
        6. Check whether the duration of the first execution is approximately
           the double of the duration of the second one as its cpu resource is
           half of the second run.
        """

        # Create function
        package = self.create_package(
            name='python/test_python_cpu_limit.py'
        )
        function_id = self.create_function(package_path=package, timeout=180)

        # Invoke function
        resp, body = self.client.create_execution(function_id)

        execution_id = body['id']
        self.addCleanup(self.client.delete_resource, 'executions',
                        execution_id, ignore_notfound=True)

        # Record the duration, check whether the result is correct.
        self.assertEqual(201, resp.status)
        result = json.loads(body['result'])
        output = result.get('output')
        # Only the first 15 digits are returned.
        self.assertEqual('314159265358979', output)
        first_duration = result.get('duration', 0)

        # Increase the cpu limit
        resp, body = self.client.update_function(function_id, cpu=200)
        self.assertEqual(200, resp.status_code)

        # Invoke the function again
        resp, body = self.client.create_execution(function_id)

        execution_id = body['id']
        self.addCleanup(self.client.delete_resource, 'executions',
                        execution_id, ignore_notfound=True)

        # Record the second duration, check whether the result is correct.
        self.assertEqual(201, resp.status)
        result = json.loads(body['result'])
        output = result.get('output')
        # Only the first 15 digits are returned.
        self.assertEqual('314159265358979', output)
        second_duration = result.get('duration', 0)

        # Check whether the duration of the first execution is approximately
        # the double (1.8x ~ 2.2x) of the duration of the second one.
        # NOTE(huntxu): on my testbed, the result is quite near 2x. However
        # it may vary in different environments, so we give a wider range
        # here.
        self.assertNotEqual(0, first_duration)
        self.assertNotEqual(0, second_duration)
        upper = second_duration * 2.5
        lower = second_duration * 1.8
        self.assertGreaterEqual(upper, first_duration)
        self.assertLessEqual(lower, first_duration)

    @decorators.idempotent_id('07edf2ff-7544-4f30-b006-fd5302a2a9cc')
    @testtools.skipUnless(CONF.qinling.allow_external_connection,
                          "External network connection is not allowed")
    def test_python_execution_public_connection(self):
        """Test connections from k8s pod to the outside.

        Create a function that reads a webpage on the Internet, to
        verify that pods in Kubernetes can connect to the outside.
        """

        # Create function
        package = self.create_package(name='python/test_python_http_get.py')
        function_id = self.create_function(package_path=package)

        url = 'https://docs.openstack.org/qinling/latest'

        # Gets the page's sha256 outside Qinling
        response = requests.get(url, timeout=10)
        page_sha256 = hashlib.sha256(response.text.encode('utf-8')).hexdigest()

        # Create an execution to get the page's sha256 with Qinling
        resp, body = self.client.create_execution(
            function_id, input='{"url": "%s"}' % url
        )
        execution_id = body['id']
        self.addCleanup(self.client.delete_resource, 'executions',
                        execution_id, ignore_notfound=True)

        self.assertEqual(201, resp.status)
        self.assertEqual('success', body['status'])
        result = json.loads(body['result'])
        self.assertEqual(page_sha256, result['output'])

    @decorators.idempotent_id('b05e3bac-b23f-11e8-9679-00224d6b7bc1')
    def test_python_execution_timeout(self):
        package = self.create_package(
            name='python/test_python_sleep.py'
        )
        function_id = self.create_function(package_path=package)

        resp, body = self.client.create_execution(
            function_id,
            input='{"seconds": 7}'
        )

        self.assertEqual(201, resp.status)
        self.addCleanup(self.client.delete_resource, 'executions',
                        body['id'], ignore_notfound=True)
        self.assertEqual('failed', body['status'])

        result = jsonutils.loads(body['result'])

        self.assertGreaterEqual(result['duration'], 5)
        self.assertIn(
            'Function execution timeout', result['output']
        )

        # Update function timeout
        resp, _ = self.client.update_function(
            function_id,
            timeout=10
        )
        self.assertEqual(200, resp.status_code)

        resp, body = self.client.create_execution(
            function_id,
            input='{"seconds": 7}'
        )

        self.assertEqual(201, resp.status)
        self.addCleanup(self.client.delete_resource, 'executions',
                        body['id'], ignore_notfound=True)
        self.assertEqual('success', body['status'])

        result = jsonutils.loads(body['result'])
        self.assertGreaterEqual(result['duration'], 7)
