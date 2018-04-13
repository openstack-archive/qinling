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
        :return: MD5 value of the package.
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

        # The md5 is contained in the package path.
        new_func_zip = os.path.join(project_path, '%s.zip.new' % function)
        func_zip = os.path.join(project_path,
                                PACKAGE_NAME_TEMPLATE % (function, md5_actual))

        # Store package
        with open(new_func_zip, 'wb') as fd:
            fd.write(data)

        if not zipfile.is_zipfile(new_func_zip):
            fileutils.delete_if_exists(new_func_zip)
            raise exc.InputException("Package is not a valid ZIP package.")

        os.rename(new_func_zip, func_zip)
        return md5_actual

    def retrieve(self, project_id, function, md5sum):
        """Get function package data.

        :param project_id: Project ID.
        :param function: Function ID.
        :param md5sum: The function MD5.
        :return: File descriptor that needs to close outside.
        """
        LOG.debug(
            'Getting package data, function: %s, md5sum: %s, project: %s',
            function, md5sum, project_id
        )

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
        LOG.debug('Found package data for function %s', function)

        return f

    def delete(self, project_id, function, md5sum):
        LOG.debug(
            'Deleting package data, function: %s, md5sum: %s, project: %s',
            function, md5sum, project_id
        )

        func_zip = os.path.join(
            self.base_path,
            PACKAGE_PATH_TEMPLATE % (project_id, function, md5sum)
        )

        if os.path.exists(func_zip):
            os.remove(func_zip)
