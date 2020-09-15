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

import abc

from stevedore import driver

from qinling import exceptions as exc

STORAGE_PROVIDER = None


class PackageStorage(object, metaclass=abc.ABCMeta):
    """PackageStorage interface."""

    @abc.abstractmethod
    def store(self, project_id, function, data, **kwargs):
        """Store the function package data.

        :param project_id: Project ID.
        :param function: Function ID.
        :param data: Package file content.
        :param kwargs: A dict may including
            - md5sum: The MD5 provided by the user.
        :return: A tuple (if the package is updated, MD5 value of the package)
        """
        raise NotImplementedError

    @abc.abstractmethod
    def retrieve(self, project_id, function, md5sum, version=0):
        """Get function package data.

        :param project_id: Project ID.
        :param function: Function ID.
        :param md5sum: The function MD5.
        :param version: Optional. The function version number.
        :return: File descriptor that needs to close outside.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, project_id, function, md5sum, version=0):
        raise NotImplementedError

    @abc.abstractmethod
    def changed_since(self, project_id, function, l_md5, version):
        """Check if the function package has changed.

        Check if the function package has changed between lastest and the
        specified version.

        :param project_id: Project ID.
        :param function: Function ID.
        :param l_md5: Latest function package md5sum.
        :param version: The version number compared with.
        :return: True if changed otherwise False.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self, project_id, function, l_md5, old_version):
        """Copy function package for a new version.

        :param project_id: Project ID.
        :param function: Function ID.
        :param l_md5: Latest function package md5sum.
        :param old_version: The version number that should copy from.
        :return: None
        """
        raise NotImplementedError


def load_storage_provider(conf):
    global STORAGE_PROVIDER

    if not STORAGE_PROVIDER:
        try:
            mgr = driver.DriverManager(
                'qinling.storage.provider',
                conf.storage.provider,
                invoke_on_load=True,
                invoke_args=[conf]
            )

            STORAGE_PROVIDER = mgr.driver
        except Exception as e:
            raise exc.StorageProviderException(
                'Failed to load storage provider: %s. Error: %s' %
                (conf.storage.provider, str(e))
            )

    return STORAGE_PROVIDER
