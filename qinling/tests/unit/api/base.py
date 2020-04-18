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

import shutil
import tempfile
from unittest import mock

from oslo_config import cfg
import pecan
import pecan.testing
from webtest import app as webtest_app

from qinling.tests.unit import base

CONF = cfg.CONF


class APITest(base.DbTestCase):
    def setUp(self):
        super(APITest, self).setUp()

        # Config package directory before app starts.
        package_dir = tempfile.mkdtemp(prefix='tmp_qinling')
        self.override_config('file_system_dir', package_dir, 'storage')
        self.addCleanup(shutil.rmtree, package_dir, True)

        # Disable authentication by default for API tests.
        self.override_config('auth_enable', False, group='pecan')

        # Disable job handler. The following pecan app instantiation will
        # invoke qinling.api.app:setup_app()
        self.override_config('enable_job_handler', False, group='api')

        pecan_opts = CONF.pecan
        self.app = pecan.testing.load_test_app({
            'app': {
                'root': pecan_opts.root,
                'modules': pecan_opts.modules,
                'debug': pecan_opts.debug,
                'auth_enable': False,
            }
        })

        self.addCleanup(pecan.set_config, {}, overwrite=True)

        self.patch_ctx = mock.patch('qinling.context.Context.from_environ')
        self.mock_ctx = self.patch_ctx.start()
        self.mock_ctx.return_value = self.ctx
        self.addCleanup(self.patch_ctx.stop)

    def _assertNotFound(self, url):
        try:
            self.app.get(url, headers={'Accept': 'application/json'})
        except webtest_app.AppError as error:
            self.assertIn('Bad response: 404 Not Found', str(error))
            return

        self.fail('Expected 404 Not found but got OK')

    def _assertUnauthorized(self, url):
        try:
            self.app.get(url, headers={'Accept': 'application/json'})
        except webtest_app.AppError as error:
            self.assertIn('Bad response: 401 Unauthorized', str(error))
            return

        self.fail('Expected 401 Unauthorized but got OK')
