# Copyright 2018 AWCloud Software Co., Ltd.
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

import mock
import os

from oslo_config import cfg

from qinling import config
from qinling import exceptions as exc
from qinling.storage import file_system
from qinling.tests.unit import base

CONF = cfg.CONF
FAKE_STORAGE_PATH = 'TMP_DIR'


class TestFileSystemStorage(base.BaseTest):
    def setUp(self):
        super(TestFileSystemStorage, self).setUp()
        CONF.register_opts(config.storage_opts, config.STORAGE_GROUP)
        self.override_config('file_system_dir', FAKE_STORAGE_PATH, 'storage')
        self.project_id = base.DEFAULT_PROJECT_ID
        self.storage = file_system.FileSystemStorage(CONF)

    @mock.patch('oslo_utils.fileutils.ensure_tree')
    @mock.patch('os.rename')
    @mock.patch('qinling.storage.file_system.open')
    @mock.patch('zipfile.is_zipfile')
    def test_store(self, is_zipfile_mock, open_mock, rename_mock,
                   ensure_tree_mock):
        is_zipfile_mock.return_value = True
        fake_fd = mock.Mock()
        open_mock.return_value.__enter__.return_value = fake_fd
        function = self.rand_name('function', prefix='TestFileSystemStorage')
        # For python3, data should be encoded into bytes before hashing.
        function_data = "Some data".encode('utf8')

        self.storage.store(self.project_id, function, function_data)

        ensure_tree_mock.assert_called_once_with(
            os.path.join(FAKE_STORAGE_PATH, self.project_id))
        fake_fd.write.assert_called_once_with(function_data)
        is_zipfile_mock.assert_called_once_with(
            os.path.join(FAKE_STORAGE_PATH, self.project_id,
                         '%s.zip.new' % function))
        rename_mock.assert_called_once_with(
            os.path.join(FAKE_STORAGE_PATH, self.project_id,
                         '%s.zip.new' % function),
            os.path.join(FAKE_STORAGE_PATH, self.project_id,
                         '%s.zip' % function))

    @mock.patch('oslo_utils.fileutils.ensure_tree')
    def test_store_md5_mismatch(self, ensure_tree_mock):
        function = self.rand_name('function', prefix='TestFileSystemStorage')
        # For python3, data should be encoded into bytes before hashing.
        function_data = "Some data".encode('utf8')
        not_a_md5sum = "Not a md5sum"

        self.assertRaisesRegexp(
            exc.InputException,
            "^Package md5 mismatch\.$",
            self.storage.store,
            self.project_id, function, function_data, md5sum=not_a_md5sum)

        ensure_tree_mock.assert_called_once_with(
            os.path.join(FAKE_STORAGE_PATH, self.project_id))

    @mock.patch('oslo_utils.fileutils.delete_if_exists')
    @mock.patch('oslo_utils.fileutils.ensure_tree')
    @mock.patch('qinling.storage.file_system.open')
    @mock.patch('zipfile.is_zipfile')
    def test_store_invalid_zip_package(
        self, is_zipfile_mock, open_mock,
        ensure_tree_mock, delete_if_exists_mock
    ):
        is_zipfile_mock.return_value = False
        fake_fd = mock.Mock()
        open_mock.return_value.__enter__.return_value = fake_fd
        function = self.rand_name('function', prefix='TestFileSystemStorage')
        # For python3, data should be encoded into bytes before hashing.
        function_data = "Some data".encode('utf8')

        self.assertRaisesRegexp(
            exc.InputException,
            "^Package is not a valid ZIP package\.$",
            self.storage.store,
            self.project_id, function, function_data)

        ensure_tree_mock.assert_called_once_with(
            os.path.join(FAKE_STORAGE_PATH, self.project_id))
        fake_fd.write.assert_called_once_with(function_data)
        delete_if_exists_mock.assert_called_once_with(
            os.path.join(FAKE_STORAGE_PATH, self.project_id,
                         '%s.zip.new' % function))

    @mock.patch('os.path.exists')
    @mock.patch('qinling.storage.file_system.open')
    def test_retrieve(self, open_mock, exists_mock):
        exists_mock.return_value = True
        fake_fd = mock.Mock()
        open_mock.return_value = fake_fd
        function = self.rand_name('function', prefix='TestFileSystemStorage')

        ret = self.storage.retrieve(self.project_id, function)

        exists_mock.assert_called_once_with(
            os.path.join(FAKE_STORAGE_PATH, self.project_id,
                         '%s.zip' % function))
        open_mock.assert_called_once_with(
            os.path.join(FAKE_STORAGE_PATH, self.project_id,
                         '%s.zip' % function),
            'rb')
        self.assertEqual(fake_fd, ret)

    @mock.patch('os.path.exists')
    def test_retrieve_package_not_found(self, exists_mock):
        exists_mock.return_value = False
        function = self.rand_name('function', prefix='TestFileSystemStorage')

        self.assertRaisesRegexp(
            exc.StorageNotFoundException,
            "^Package of function %s for project %s not found\.$" % (
                function, self.project_id),
            self.storage.retrieve,
            self.project_id, function)

        exists_mock.assert_called_once_with(
            os.path.join(FAKE_STORAGE_PATH, self.project_id,
                         '%s.zip' % function))

    @mock.patch('os.path.exists')
    @mock.patch('os.remove')
    def test_delete(self, remove_mock, exists_mock):
        exists_mock.return_value = True
        function = self.rand_name('function', prefix='TestFileSystemStorage')

        self.storage.delete(self.project_id, function)

        exists_mock.assert_called_once_with(
            os.path.join(FAKE_STORAGE_PATH, self.project_id,
                         '%s.zip' % function))
        remove_mock.assert_called_once_with(
            os.path.join(FAKE_STORAGE_PATH, self.project_id,
                         '%s.zip' % function))

    @mock.patch('os.path.exists')
    @mock.patch('os.remove')
    def test_delete_package_not_exists(self, remove_mock, exists_mock):
        exists_mock.return_value = False
        function = self.rand_name('function', prefix='TestFileSystemStorage')

        self.storage.delete(self.project_id, function)

        exists_mock.assert_called_once_with(
            os.path.join(FAKE_STORAGE_PATH, self.project_id,
                         '%s.zip' % function))
        remove_mock.assert_not_called()
