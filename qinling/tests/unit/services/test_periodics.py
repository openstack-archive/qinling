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
from datetime import datetime
from datetime import timedelta
import time
from unittest import mock

from oslo_config import cfg

from qinling import context
from qinling.db import api as db_api
from qinling.services import periodics
from qinling import status
from qinling.tests.unit import base

CONF = cfg.CONF


class TestPeriodics(base.DbTestCase):
    def setUp(self):
        super(TestPeriodics, self).setUp()
        self.override_config('auth_enable', False, group='pecan')

    @mock.patch('qinling.utils.etcd_util.delete_function')
    @mock.patch('qinling.utils.etcd_util.get_service_url')
    def test_handle_function_service_no_function_version(self, mock_etcd_url,
                                                         mock_etcd_delete):
        db_func = self.create_function()
        function_id = db_func.id
        # Update function to simulate function execution
        db_api.update_function(function_id, {'count': 1})
        time.sleep(1.5)

        mock_etcd_url.return_value = 'http://localhost:37718'
        self.override_config('function_service_expiration', 1, 'engine')
        mock_engine = mock.Mock()

        periodics.handle_function_service_expiration(self.ctx, mock_engine)

        mock_engine.delete_function.assert_called_once_with(
            self.ctx, function_id, 0
        )
        mock_etcd_delete.assert_called_once_with(function_id, 0)

    @mock.patch('qinling.utils.etcd_util.delete_function')
    @mock.patch('qinling.utils.etcd_util.get_service_url')
    def test_handle_function_service_with_function_versions(self, mock_srv_url,
                                                            mock_etcd_delete):
        db_func = self.create_function()
        function_id = db_func.id
        self.create_function_version(0, function_id, description="new_version")
        db_api.update_function_version(function_id, 1, count=1)
        time.sleep(1.5)

        self.override_config('function_service_expiration', 1, 'engine')

        # NOTE(huntxu): although we didn't create any execution using version 0
        # of the function, it is updated as a new version is created. So the
        # call to get_service_url with version 0 should return None as there is
        # not any worker for function version 0.
        def mock_srv_url_side_effect(function_id, function_version):
            return 'http://localhost:37718' if function_version != 0 else None

        mock_srv_url.side_effect = mock_srv_url_side_effect
        mock_engine = mock.Mock()

        periodics.handle_function_service_expiration(self.ctx, mock_engine)

        mock_engine.delete_function.assert_called_once_with(
            self.ctx, function_id, 1
        )
        mock_etcd_delete.assert_called_once_with(function_id, 1)

    @mock.patch('qinling.utils.etcd_util.delete_function')
    @mock.patch('qinling.utils.etcd_util.get_service_url')
    def test_handle_function_service_with_versioned_function_version_0(
            self, mock_srv_url, mock_etcd_delete
    ):
        # This case tests that if a function has multiple versions, service
        # which serves executions of function version 0 is correctly handled
        # when expired.
        db_func = self.create_function()
        function_id = db_func.id
        self.create_function_version(0, function_id, description="new_version")
        # Simulate an execution using version 0
        db_api.update_function(function_id, {'count': 1})
        time.sleep(1.5)

        self.override_config('function_service_expiration', 1, 'engine')
        mock_srv_url.return_value = 'http://localhost:37718'
        mock_engine = mock.Mock()

        periodics.handle_function_service_expiration(self.ctx, mock_engine)

        mock_engine.delete_function.assert_called_once_with(
            self.ctx, function_id, 0
        )
        mock_etcd_delete.assert_called_once_with(function_id, 0)

    @mock.patch('qinling.utils.jobs.get_next_execution_time')
    def test_job_handler(self, mock_get_next):
        db_func = self.create_function()
        function_id = db_func.id

        self.assertEqual(0, db_func.count)

        now = datetime.utcnow()
        db_job = self.create_job(
            function_id=function_id,
            status=status.RUNNING,
            next_execution_time=now,
            count=2
        )
        job_id = db_job.id

        e_client = mock.Mock()
        mock_get_next.return_value = now + timedelta(seconds=1)

        periodics.handle_job(e_client)
        context.set_ctx(self.ctx)

        db_job = db_api.get_job(job_id)
        self.assertEqual(1, db_job.count)
        db_func = db_api.get_function(function_id)
        self.assertEqual(1, db_func.count)
        db_execs = db_api.get_executions(function_id=function_id)
        self.assertEqual(1, len(db_execs))

        periodics.handle_job(e_client)
        context.set_ctx(self.ctx)

        db_job = db_api.get_job(job_id)
        self.assertEqual(0, db_job.count)
        self.assertEqual(status.DONE, db_job.status)
        db_func = db_api.get_function(function_id)
        self.assertEqual(2, db_func.count)
        db_execs = db_api.get_executions(function_id=function_id)
        self.assertEqual(2, len(db_execs))

    @mock.patch('qinling.utils.jobs.get_next_execution_time')
    def test_job_handler_with_version(self, mock_next_time):
        db_func = self.create_function()
        function_id = db_func.id
        new_version = db_api.increase_function_version(function_id, 0)

        self.assertEqual(0, new_version.count)

        now = datetime.utcnow()
        db_job = self.create_job(
            function_id,
            function_version=1,
            status=status.RUNNING,
            next_execution_time=now,
            count=2
        )
        job_id = db_job.id

        e_client = mock.Mock()
        # It doesn't matter what's the returned value, but need to be in
        # datetime type.
        mock_next_time.return_value = now + timedelta(seconds=1)

        periodics.handle_job(e_client)
        context.set_ctx(self.ctx)

        db_job = db_api.get_job(job_id)
        self.assertEqual(1, db_job.count)
        db_func = db_api.get_function(function_id)
        self.assertEqual(0, db_func.count)
        db_version = db_api.get_function_version(function_id, 1)
        self.assertEqual(1, db_version.count)
        db_execs = db_api.get_executions(function_id=function_id,
                                         function_version=1)
        self.assertEqual(1, len(db_execs))

        periodics.handle_job(e_client)
        context.set_ctx(self.ctx)

        db_job = db_api.get_job(job_id)
        self.assertEqual(0, db_job.count)
        self.assertEqual(status.DONE, db_job.status)
        db_func = db_api.get_function(function_id)
        self.assertEqual(0, db_func.count)
        db_version = db_api.get_function_version(function_id, 1)
        self.assertEqual(2, db_version.count)
        db_execs = db_api.get_executions(function_id=function_id,
                                         function_version=1)
        self.assertEqual(2, len(db_execs))

    @mock.patch('qinling.utils.jobs.get_next_execution_time')
    def test_job_handler_with_alias(self, mock_next_time):
        e_client = mock.Mock()
        now = datetime.utcnow()
        # It doesn't matter what's the returned value, but need to be in
        # datetime type.
        mock_next_time.return_value = now + timedelta(seconds=1)

        # Create a alias for a function.
        alias_name = self.rand_name(name="alias", prefix=self.prefix)
        db_func = self.create_function()
        function_id = db_func.id
        db_api.create_function_alias(name=alias_name, function_id=function_id)

        self.create_job(
            function_alias=alias_name,
            status=status.RUNNING,
            next_execution_time=now,
        )

        periodics.handle_job(e_client)
        context.set_ctx(self.ctx)

        # Create function version 1 and update the alias.
        db_api.increase_function_version(function_id, 0)
        db_api.update_function_alias(alias_name, function_version=1)

        periodics.handle_job(e_client)
        context.set_ctx(self.ctx)

        db_func = db_api.get_function(function_id)
        self.assertEqual(1, db_func.count)
        db_version = db_api.get_function_version(function_id, 1)
        self.assertEqual(1, db_version.count)
        db_execs = db_api.get_executions(function_id=function_id)
        self.assertEqual(2, len(db_execs))
