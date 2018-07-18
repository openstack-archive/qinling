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

from oslo_log import log as logging
from swiftclient.exceptions import ClientException

from qinling import exceptions as exc
from qinling.utils import common
from qinling.utils import constants
from qinling.utils.openstack import keystone

LOG = logging.getLogger(__name__)


@common.disable_ssl_warnings
def check_object(container, object):
    """Check object in Swift.

    1. If the object exists.
    2. Object size.

    :param container: Container name.
    :param object: Object name.
    :return: True if object exists, otherwise return False.
    """
    swift_conn = keystone.get_swiftclient()

    try:
        header = swift_conn.head_object(container, object)
    except ClientException:
        LOG.error(
            'The object %s in container %s was not found', object, container
        )
        return False
    except Exception:
        LOG.exception("Error when communicating with Swift.")
        return False

    if int(header['content-length']) > constants.MAX_PACKAGE_SIZE:
        LOG.error('Object size is greater than %s', constants.MAX_PACKAGE_SIZE)
        return False

    return True


@common.disable_ssl_warnings
def download_object(container, object):
    swift_conn = keystone.get_swiftclient()

    try:
        # Specify 'resp_chunk_size' here to return a file reader.
        _, obj_reader = swift_conn.get_object(
            container, object, resp_chunk_size=65536
        )
    except Exception:
        LOG.exception("Error when downloading object from Swift.")
        raise exc.SwiftException()

    return obj_reader
