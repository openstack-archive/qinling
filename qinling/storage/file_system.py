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

import os
import shutil
import zipfile

from oslo_log import log as logging
from oslo_utils import fileutils

from qinling import exceptions as exc
from qinling.storage import base
from qinling.utils import common

LOG = logging.getLogger(__name__)
PACKAGE_NAME_TEMPLATE = "%s_%s.zip"
# Package path name including project ID
PACKAGE_PATH_TEMPLATE = "%s/%s_%s.zip"
# Package path name including version
PACKAGE_VERSION_TEMPLATE = "%s_%s_%s.zip"


class FileSystemStorage(base.PackageStorage):
    """Interact with file system for function package storage."""

    def __init__(self, conf):
        self.base_path = conf.storage.file_system_dir

    def store(self, project_id, function, data, md5sum=None):
        """Store the function package data to local file system.

        :param project_id: Project ID.
        :param function: Function ID.
        :param data: Package file content.
        :param md5sum: The MD5 provided by the user.
        :return: A tuple (if the package is updated, MD5 value of the package)
        """
        LOG.debug(
            'Store package, function: %s, project: %s', function, project_id
        )

        project_path = os.path.join(self.base_path, project_id)
        fileutils.ensure_tree(project_path)

        # Check md5
        md5_actual = common.md5(content=data)
        if md5sum and md5_actual != md5sum:
            raise exc.InputException("Package md5 mismatch.")

        func_zip = os.path.join(
            project_path,
            PACKAGE_NAME_TEMPLATE % (function, md5_actual)
        )
        if os.path.exists(func_zip):
            return False, md5_actual

        # Save package
        new_func_zip = os.path.join(project_path, '%s.zip.new' % function)
        with open(new_func_zip, 'wb') as fd:
            fd.write(data)

        if not zipfile.is_zipfile(new_func_zip):
            fileutils.delete_if_exists(new_func_zip)
            raise exc.InputException("Package is not a valid ZIP package.")

        os.rename(new_func_zip, func_zip)

        return True, md5_actual

    def retrieve(self, project_id, function, md5sum, version=0):
        """Get function package data.

        If version is not 0, return the package data of that specific function
        version.

        :param project_id: Project ID.
        :param function: Function ID.
        :param md5sum: The function MD5.
        :param version: Optional. The function version number.
        :return: File descriptor that needs to close outside.
        """
        LOG.debug(
            'Getting package data, function: %s, version: %s, md5sum: %s, '
            'project: %s',
            function, version, md5sum, project_id
        )

        if version != 0:
            project_dir = os.path.join(self.base_path, project_id)
            for filename in os.listdir(project_dir):
                root, ext = os.path.splitext(filename)
                if (root.startswith("%s_%d" % (function, version))
                        and ext == '.zip'):
                    func_zip = os.path.join(project_dir, filename)
                    break
            else:
                raise exc.StorageNotFoundException(
                    'Package of version %d function %s for project %s not '
                    'found.' % (version, function, project_id)
                )
        else:
            func_zip = os.path.join(
                self.base_path,
                PACKAGE_PATH_TEMPLATE % (project_id, function, md5sum)
            )

        if not os.path.exists(func_zip):
            raise exc.StorageNotFoundException(
                'Package of function %s for project %s not found.' %
                (function, project_id)
            )

        f = open(func_zip, 'rb')
        LOG.debug('Found package data for function %s version %d', function,
                  version)

        return f

    def delete(self, project_id, function, md5sum, version=0):
        LOG.debug(
            'Deleting package data, function: %s, version: %s, md5sum: %s, '
            'project: %s',
            function, version, md5sum, project_id
        )

        if version != 0:
            project_dir = os.path.join(self.base_path, project_id)
            for filename in os.listdir(project_dir):
                root, ext = os.path.splitext(filename)
                if (root.startswith("%s_%d" % (function, version))
                        and ext == '.zip'):
                    func_zip = os.path.join(project_dir, filename)
                    break
            else:
                return
        else:
            func_zip = os.path.join(
                self.base_path,
                PACKAGE_PATH_TEMPLATE % (project_id, function, md5sum)
            )

        if os.path.exists(func_zip):
            os.remove(func_zip)

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
        # If it's the first version creation, don't check.
        if version == 0:
            return True

        version_path = os.path.join(
            self.base_path, project_id,
            PACKAGE_VERSION_TEMPLATE % (function, version, l_md5)
        )
        if os.path.exists(version_path):
            return False

        return True

    def copy(self, project_id, function, l_md5, old_version):
        """Copy function package for a new version.

        :param project_id: Project ID.
        :param function: Function ID.
        :param l_md5: Latest function package md5sum.
        :param old_version: The version number that should copy from.
        :return: None
        """
        src_package = os.path.join(self.base_path,
                                   project_id,
                                   PACKAGE_NAME_TEMPLATE % (function, l_md5)
                                   )
        dest_package = os.path.join(self.base_path,
                                    project_id,
                                    PACKAGE_VERSION_TEMPLATE %
                                    (function, old_version + 1, l_md5))

        try:
            shutil.copyfile(src_package, dest_package)
        except Exception:
            msg = "Failed to create new function version."
            LOG.exception(msg)
            raise exc.StorageProviderException(msg)
