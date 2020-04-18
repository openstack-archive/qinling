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

import os
from unittest import mock

from oslo_config import cfg

from qinling import config
from qinling import exceptions as exc
from qinling.storage import file_system
from qinling.tests.unit import base
from qinling.utils import common

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
        md5 = common.md5(content=function_data)

        package_updated, ret_md5 = self.storage.store(
            self.project_id, function, function_data
        )

        self.assertTrue(package_updated)
        self.assertEqual(md5, ret_md5)

        temp_package_path = os.path.join(FAKE_STORAGE_PATH, self.project_id,
                                         '%s.zip.new' % function)
        package_path = os.path.join(
            FAKE_STORAGE_PATH,
            file_system.PACKAGE_PATH_TEMPLATE % (self.project_id, function,
                                                 md5)
        )
        ensure_tree_mock.assert_called_once_with(
            os.path.join(FAKE_STORAGE_PATH, self.project_id)
        )
        fake_fd.write.assert_called_once_with(function_data)
        is_zipfile_mock.assert_called_once_with(temp_package_path)
        rename_mock.assert_called_once_with(temp_package_path, package_path)

    @mock.patch('oslo_utils.fileutils.ensure_tree')
    @mock.patch('os.path.exists')
    def test_store_zip_exists(self, exists_mock, ensure_tree_mock):
        function = self.rand_name('function', prefix='TestFileSystemStorage')
        function_data = "Some data".encode('utf8')
        md5 = common.md5(content=function_data)
        exists_mock.return_value = True

        package_updated, ret_md5 = self.storage.store(
            self.project_id, function, function_data
        )

        self.assertFalse(package_updated)
        self.assertEqual(md5, ret_md5)

        package_path = os.path.join(
            FAKE_STORAGE_PATH,
            file_system.PACKAGE_PATH_TEMPLATE % (self.project_id, function,
                                                 md5)
        )

        exists_mock.assert_called_once_with(package_path)

    @mock.patch('oslo_utils.fileutils.ensure_tree')
    def test_store_md5_mismatch(self, ensure_tree_mock):
        function = self.rand_name('function', prefix='TestFileSystemStorage')
        # For python3, data should be encoded into bytes before hashing.
        function_data = "Some data".encode('utf8')
        not_a_md5sum = "Not a md5sum"

        self.assertRaisesRegex(
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

        self.assertRaisesRegex(
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

        ret = self.storage.retrieve(self.project_id, function, "fake_md5")

        package_path = os.path.join(
            FAKE_STORAGE_PATH,
            file_system.PACKAGE_PATH_TEMPLATE % (self.project_id, function,
                                                 "fake_md5")
        )
        exists_mock.assert_called_once_with(package_path)
        open_mock.assert_called_once_with(package_path, 'rb')
        self.assertEqual(fake_fd, ret)

    @mock.patch('os.path.exists')
    def test_retrieve_package_not_found(self, exists_mock):
        exists_mock.return_value = False
        function = self.rand_name('function', prefix='TestFileSystemStorage')

        self.assertRaisesRegex(
            exc.StorageNotFoundException,
            "^Package of function %s for project %s not found\.$" % (
                function, self.project_id),
            self.storage.retrieve,
            self.project_id,
            function,
            "fake_md5"
        )

        package_path = os.path.join(
            FAKE_STORAGE_PATH,
            file_system.PACKAGE_PATH_TEMPLATE % (self.project_id, function,
                                                 "fake_md5")
        )
        exists_mock.assert_called_once_with(package_path)

    @mock.patch('qinling.storage.file_system.open')
    @mock.patch('os.path.exists')
    @mock.patch('os.listdir')
    def test_retrieve_version(self, mock_list, mock_exist, mock_open):
        function = "fake_function_id"
        version = 1
        md5 = "md5"
        mock_list.return_value = ["%s_%s_%s.zip" % (function, version, md5)]
        mock_exist.return_value = True

        self.storage.retrieve(self.project_id, function, None,
                              version=version)

        version_zip = os.path.join(FAKE_STORAGE_PATH, self.project_id,
                                   "%s_%s_%s.zip" % (function, version, md5))

        mock_exist.assert_called_once_with(version_zip)

    @mock.patch('os.listdir')
    def test_retrieve_version_not_found(self, mock_list):
        function = "fake_function_id"
        version = 1
        mock_list.return_value = [""]

        self.assertRaises(
            exc.StorageNotFoundException,
            self.storage.retrieve,
            function,
            self.project_id,
            None,
            version=version
        )

    @mock.patch('os.path.exists')
    @mock.patch('os.remove')
    def test_delete(self, remove_mock, exists_mock):
        exists_mock.return_value = True
        function = self.rand_name('function', prefix='TestFileSystemStorage')

        self.storage.delete(self.project_id, function, "fake_md5")

        package_path = os.path.join(
            FAKE_STORAGE_PATH,
            file_system.PACKAGE_PATH_TEMPLATE % (self.project_id, function,
                                                 "fake_md5")
        )
        exists_mock.assert_called_once_with(package_path)
        remove_mock.assert_called_once_with(package_path)

    @mock.patch('os.path.exists')
    @mock.patch('os.remove')
    @mock.patch('os.listdir')
    def test_delete_with_version(self, mock_list, remove_mock, exists_mock):
        exists_mock.return_value = True
        function = self.rand_name('function', prefix='TestFileSystemStorage')
        version = 1
        mock_list.return_value = ["%s_%s_md5.zip" % (function, version)]

        self.storage.delete(self.project_id, function, "fake_md5", version=1)

        package_path = os.path.join(
            FAKE_STORAGE_PATH,
            self.project_id,
            file_system.PACKAGE_VERSION_TEMPLATE % (function, version, "md5")
        )
        exists_mock.assert_called_once_with(package_path)
        remove_mock.assert_called_once_with(package_path)

    @mock.patch('os.path.exists')
    @mock.patch('os.remove')
    def test_delete_package_not_exists(self, remove_mock, exists_mock):
        exists_mock.return_value = False
        function = self.rand_name('function', prefix='TestFileSystemStorage')

        self.storage.delete(self.project_id, function, "fake_md5")

        package_path = os.path.join(
            FAKE_STORAGE_PATH,
            file_system.PACKAGE_PATH_TEMPLATE % (self.project_id, function,
                                                 "fake_md5")
        )
        exists_mock.assert_called_once_with(package_path)
        remove_mock.assert_not_called()

    def test_changed_since_first_version(self):
        ret = self.storage.changed_since(self.project_id, "fake_function",
                                         "fake_md5", 0)

        self.assertTrue(ret)

    @mock.patch('os.path.exists')
    def test_changed_since_exists(self, mock_exists):
        mock_exists.return_value = True

        ret = self.storage.changed_since(self.project_id, "fake_function",
                                         "fake_md5", 1)

        self.assertFalse(ret)

        expect_path = os.path.join(FAKE_STORAGE_PATH, self.project_id,
                                   "fake_function_1_fake_md5.zip")

        mock_exists.assert_called_once_with(expect_path)

    @mock.patch('os.path.exists')
    def test_changed_since_not_exists(self, mock_exists):
        mock_exists.return_value = False

        ret = self.storage.changed_since(self.project_id, "fake_function",
                                         "fake_md5", 1)

        self.assertTrue(ret)

        expect_path = os.path.join(FAKE_STORAGE_PATH, self.project_id,
                                   "fake_function_1_fake_md5.zip")

        mock_exists.assert_called_once_with(expect_path)

    @mock.patch("shutil.copyfile")
    def test_copy(self, mock_copy):
        self.storage.copy(self.project_id, "fake_function", "fake_md5", 0)

        expect_src = os.path.join(FAKE_STORAGE_PATH, self.project_id,
                                  "fake_function_fake_md5.zip")
        expect_dest = os.path.join(FAKE_STORAGE_PATH, self.project_id,
                                   "fake_function_1_fake_md5.zip")

        mock_copy.assert_called_once_with(expect_src, expect_dest)
