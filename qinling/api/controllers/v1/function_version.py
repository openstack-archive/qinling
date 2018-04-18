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

from oslo_config import cfg
from oslo_log import log as logging
from pecan import rest
import tenacity
import wsmeext.pecan as wsme_pecan

from qinling.api import access_control as acl
from qinling.api.controllers.v1 import resources
from qinling.api.controllers.v1 import types
from qinling import context
from qinling.db import api as db_api
from qinling import exceptions as exc
from qinling.storage import base as storage_base
from qinling.utils import constants
from qinling.utils import etcd_util
from qinling.utils import rest_utils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class FunctionVersionsController(rest.RestController):
    def __init__(self, *args, **kwargs):
        self.type = 'function_version'
        self.storage_provider = storage_base.load_storage_provider(CONF)

        super(FunctionVersionsController, self).__init__(*args, **kwargs)

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        stop=tenacity.stop_after_attempt(30),
        retry=(tenacity.retry_if_result(lambda result: result is False))
    )
    def _create_function_version(self, project_id, function_id, **kwargs):
        with etcd_util.get_function_version_lock(function_id) as lock:
            if not lock.is_acquired():
                return False

            with db_api.transaction():
                # Get latest function package md5 and version number
                func_db = db_api.get_function(function_id)
                if func_db.code['source'] != constants.PACKAGE_FUNCTION:
                    raise exc.NotAllowedException(
                        "Function versioning only allowed for %s type "
                        "function." %
                        constants.PACKAGE_FUNCTION
                    )

                l_md5 = func_db.code['md5sum']
                l_version = func_db.latest_version

                if len(func_db.versions) >= constants.MAX_VERSION_NUMBER:
                    raise exc.NotAllowedException(
                        'Can not exceed maximum number(%s) of versions' %
                        constants.MAX_VERSION_NUMBER
                    )

                # Check if the latest package changed since last version
                changed = self.storage_provider.changed_since(project_id,
                                                              function_id,
                                                              l_md5,
                                                              l_version)
                if not changed:
                    raise exc.NotAllowedException(
                        'Function package not changed since the latest '
                        'version %s.' % l_version
                    )

                LOG.info("Creating %s, function_id: %s, old_version: %d",
                         self.type, function_id, l_version)

                # Create new version and copy package.
                self.storage_provider.copy(project_id, function_id, l_md5,
                                           l_version)
                version = db_api.increase_function_version(function_id,
                                                           l_version,
                                                           **kwargs)
                func_db.latest_version = l_version + 1

            LOG.info("New version %d for function %s created.", l_version + 1,
                     function_id)
            return version

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(
        resources.FunctionVersion,
        types.uuid,
        body=resources.FunctionVersion,
        status_code=201
    )
    def post(self, function_id, body):
        """Create a new version for the function.

        The supported boy params:
            - description: Optional. The description of the new version.
        """
        ctx = context.get_ctx()
        acl.enforce('function_version:create', ctx)

        params = body.to_dict()
        values = {
            'description': params.get('description'),
        }

        # Try to create a new function version within lock and db transaction
        version = self._create_function_version(ctx.project_id, function_id,
                                                **values)

        return resources.FunctionVersion.from_dict(version.to_dict())

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.FunctionVersions, types.uuid)
    def get_all(self, function_id):
        acl.enforce('function_version:get_all', context.get_ctx())
        LOG.info("Getting function versions for function %s.", function_id)

        # Getting function and versions needs to happen in a db transaction
        with db_api.transaction():
            func_db = db_api.get_function(function_id)
            db_versions = func_db.versions

        versions = [resources.FunctionVersion.from_dict(v.to_dict())
                    for v in db_versions]

        return resources.FunctionVersions(function_versions=versions)
