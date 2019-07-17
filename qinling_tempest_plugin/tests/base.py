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
import pkg_resources
import tempfile
import zipfile

from tempest import config
from tempest.lib.common.utils import data_utils
from tempest import test
import tenacity

CONF = config.CONF


class BaseQinlingTest(test.BaseTestCase):
    credentials = ('admin', 'primary', 'alt')
    create_runtime = True
    image = CONF.qinling.python_runtime_image

    @classmethod
    def skip_checks(cls):
        super(BaseQinlingTest, cls).skip_checks()

        if not CONF.service_available.qinling:
            raise cls.skipException("Qinling service is not available.")

    @classmethod
    def setup_clients(cls):
        super(BaseQinlingTest, cls).setup_clients()

        cls.client = cls.os_primary.qinling.QinlingClient()
        cls.alt_client = cls.os_alt.qinling.QinlingClient()
        cls.admin_client = cls.os_admin.qinling.QinlingClient()

    @classmethod
    def resource_setup(cls):
        super(BaseQinlingTest, cls).resource_setup()

        if cls.create_runtime:
            cls.runtime_id = None
            name = data_utils.rand_name('runtime', prefix=cls.name_prefix)
            _, body = cls.admin_client.create_runtime(cls.image, name)
            cls.runtime_id = body['id']

    @classmethod
    def resource_cleanup(cls):
        if cls.create_runtime and cls.runtime_id:
            cls.admin_client.delete_resource(
                'runtimes', cls.runtime_id,
                ignore_notfound=True
            )

        super(BaseQinlingTest, cls).resource_cleanup()

    @tenacity.retry(
        wait=tenacity.wait_fixed(3),
        stop=tenacity.stop_after_attempt(20),
        retry=tenacity.retry_if_exception_type(AssertionError)
    )
    def wait_runtime_available(self, id):
        resp, body = self.client.get_resource('runtimes', id)

        self.assertEqual(200, resp.status)
        self.assertEqual('available', body['status'])

    @tenacity.retry(
        wait=tenacity.wait_fixed(3),
        stop=tenacity.stop_after_attempt(10),
        retry=tenacity.retry_if_exception_type(AssertionError)
    )
    def wait_execution_success(self, id):
        resp, body = self.client.get_resource('executions', id)

        self.assertEqual(200, resp.status)
        self.assertEqual('success', body['status'])

    @tenacity.retry(
        wait=tenacity.wait_fixed(10),
        stop=tenacity.stop_after_attempt(12),
        retry=tenacity.retry_if_exception_type(AssertionError)
    )
    def wait_job_done(self, id):
        resp, body = self.client.get_resource('jobs', id)

        self.assertEqual(200, resp.status)
        self.assertEqual('done', body['status'])

    def create_package(self, name="python/test_python_basic.py"):
        file_path = pkg_resources.resource_filename(
            'qinling_tempest_plugin',
            "functions/%s" % name
        )
        base_name, extension = os.path.splitext(file_path)
        module_name = os.path.basename(base_name)
        temp_dir = tempfile.mkdtemp()
        zip_file = os.path.join(temp_dir, '%s.zip' % module_name)

        if not os.path.isfile(zip_file):
            zf = zipfile.ZipFile(zip_file, mode='w')
            try:
                zf.write(file_path, '%s%s' % (module_name, extension))
            finally:
                zf.close()

        self.addCleanup(os.rmdir, temp_dir)
        self.addCleanup(os.remove, zip_file)
        return zip_file

    def create_function(self, package_path=None, image=None,
                        md5sum=None, timeout=None):
        function_name = data_utils.rand_name(
            'function',
            prefix=self.name_prefix
        )

        if not image:
            if not package_path:
                package_path = self.create_package()

            code = {"source": "package"}
            if md5sum:
                code.update({"md5sum": md5sum})
            base_name, _ = os.path.splitext(package_path)
            module_name = os.path.basename(base_name)
            with open(package_path, 'rb') as package_data:
                resp, body = self.client.create_function(
                    code,
                    self.runtime_id,
                    name=function_name,
                    package_data=package_data,
                    entry='%s.main' % module_name,
                    timeout=timeout
                )
        else:
            resp, body = self.client.create_function(
                {"source": "image", "image": image},
                None,
                name=function_name,
            )

        self.assertEqual(201, resp.status_code)
        function_id = body['id']
        self.addCleanup(self.client.delete_resource, 'functions',
                        function_id, ignore_notfound=True)

        return function_id

    def update_function_package(self, function_id, function_path):
        package_path = self.create_package(name=function_path)
        base_name, _ = os.path.splitext(package_path)
        module_name = os.path.basename(base_name)

        with open(package_path, 'rb') as package_data:
            resp, _ = self.client.update_function(
                function_id,
                package_data=package_data,
                entry='%s.main' % module_name
            )

        self.assertEqual(200, resp.status_code)

    def create_webhook(self, function_id=None, function_alias=None,
                       version=0):
        if function_alias:
            resp, body = self.client.create_webhook(
                function_alias=function_alias
            )
        else:
            if not function_id:
                function_id = self.create_function()
            resp, body = self.client.create_webhook(
                function_id,
                version=version
            )
        self.assertEqual(201, resp.status)

        webhook_id = body['id']
        self.addCleanup(self.client.delete_resource, 'webhooks',
                        webhook_id, ignore_notfound=True)

        return webhook_id, body['webhook_url']

    def create_job(self, function_id=None, function_alias=None, version=0,
                   first_execution_time=None):
        if function_alias:
            resp, body = self.client.create_job(
                function_alias=function_alias,
                first_execution_time=first_execution_time
            )
        else:
            if not function_id:
                function_id = self.create_function()
            resp, body = self.client.create_job(
                function_id,
                version=version,
                first_execution_time=first_execution_time
            )
        self.assertEqual(201, resp.status)
        job_id = body['id']

        self.addCleanup(self.client.delete_resource, 'jobs',
                        job_id, ignore_notfound=True)

        return job_id

    def create_function_version(self, function_id=None):
        if not function_id:
            function_id = self.create_function()

        resp, body = self.client.create_function_version(function_id)
        self.assertEqual(201, resp.status)

        version = body['version_number']

        self.addCleanup(self.client.delete_function_version, function_id,
                        version, ignore_notfound=True)

        return version

    def create_execution(self, function_id=None, alias_name=None, version=0,
                         input=None):
        if alias_name:
            resp, body = self.client.create_execution(alias_name=alias_name,
                                                      input=input)
        else:
            resp, body = self.client.create_execution(function_id,
                                                      version=version,
                                                      input=input)

        self.assertEqual(201, resp.status)

        execution_id = body['id']
        self.addCleanup(self.client.delete_resource, 'executions',
                        execution_id, ignore_notfound=True)

        self.assertEqual('success', body['status'])

        return execution_id

    def create_function_alias(self, function_id=None, function_version=0):
        name = data_utils.rand_name(name="alias", prefix=self.name_prefix)
        if not function_id:
            function_id = self.create_function()

        resp, body = self.client.create_function_alias(name,
                                                       function_id,
                                                       function_version)

        self.assertEqual(201, resp.status)

        alias_name = body['name']
        self.addCleanup(self.client.delete_function_alias, alias_name,
                        ignore_notfound=True)

        return alias_name
