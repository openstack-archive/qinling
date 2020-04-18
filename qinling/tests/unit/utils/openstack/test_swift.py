# Copyright 2018 Catalyst IT Limited
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

from unittest import mock

from swiftclient.exceptions import ClientException

from qinling import exceptions as exc
from qinling.tests.unit import base
from qinling.utils import constants
from qinling.utils.openstack import swift


class TestSwift(base.BaseTest):
    @mock.patch("qinling.utils.openstack.keystone.get_swiftclient")
    def test_check_object(self, mock_sclient):
        length = constants.MAX_PACKAGE_SIZE - 1
        mock_sclient.return_value.head_object.return_value = {
            "content-length": length
        }

        ret = swift.check_object("fake_container", "fake_object")

        self.assertTrue(ret)

    @mock.patch("qinling.utils.openstack.keystone.get_swiftclient")
    def test_check_object_client_exception(self, mock_sclient):
        mock_sclient.return_value.head_object.side_effect = ClientException

        ret = swift.check_object("fake_container", "fake_object")

        self.assertFalse(ret)

    @mock.patch("qinling.utils.openstack.keystone.get_swiftclient")
    def test_check_object_other_exception(self, mock_sclient):
        mock_sclient.return_value.head_object.side_effect = Exception

        ret = swift.check_object("fake_container", "fake_object")

        self.assertFalse(ret)

    @mock.patch("qinling.utils.openstack.keystone.get_swiftclient")
    def test_check_object_invalid_length(self, mock_sclient):
        length = constants.MAX_PACKAGE_SIZE + 1
        mock_sclient.return_value.head_object.return_value = {
            "content-length": length
        }

        ret = swift.check_object("fake_container", "fake_object")

        self.assertFalse(ret)

    @mock.patch("qinling.utils.openstack.keystone.get_swiftclient")
    def test_download_object(self, mock_sclient):
        mock_get = mock.MagicMock()
        mock_get.return_value = (mock.ANY, mock.ANY)
        mock_sclient.return_value.get_object = mock_get
        swift.download_object("fake_container", "fake_object")

        mock_get.assert_called_once_with(
            "fake_container", "fake_object",
            resp_chunk_size=65536
        )

    @mock.patch("qinling.utils.openstack.keystone.get_swiftclient")
    def test_download_object_exception(self, mock_sclient):
        mock_sclient.return_value.get_object.side_effect = Exception

        self.assertRaises(
            exc.SwiftException,
            swift.download_object,
            "fake_container",
            "fake_object"
        )
