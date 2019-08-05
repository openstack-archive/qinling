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
from oslo_serialization import jsonutils

from qinling.db import api as db_api
from qinling.db.sqlalchemy import models
from qinling import exceptions as exc
from qinling import status
from qinling.utils import constants

LOG = logging.getLogger(__name__)


def _update_function_db(function_id, pre_count):
    # Function update is done using UPDATE ... FROM ... WHERE
    # non-locking clause.
    while True:
        modified = db_api.conditional_update(
            models.Function,
            {
                'count': pre_count + 1,
            },
            {
                'id': function_id,
                'count': pre_count
            },
            insecure=True,
        )
        if not modified:
            LOG.warning("Retrying to update function count.")
            pre_count += 1
            continue
        else:
            break


def _update_function_version_db(version_id, pre_count):
    # Update is done using UPDATE ... FROM ... WHERE non-locking clause.
    while True:
        modified = db_api.conditional_update(
            models.FunctionVersion,
            {
                'count': pre_count + 1,
            },
            {
                'id': version_id,
                'count': pre_count
            },
            insecure=True,
        )
        if not modified:
            LOG.warning("Retrying to update function version count.")
            pre_count += 1
            continue
        else:
            break


def create_execution(engine_client, params):
    function_alias = params.get('function_alias')
    function_id = params.get('function_id')
    version = params.get('function_version', 0)
    is_sync = params.get('sync', True)
    input = params.get('input')

    if function_alias:
        alias_db = db_api.get_function_alias(function_alias)
        function_id = alias_db.function_id
        version = alias_db.function_version
        params.update({'function_id': function_id,
                       'function_version': version})

    func_db = db_api.get_function(function_id)
    runtime_id = func_db.runtime_id

    # Image type function does not need runtime
    if runtime_id:
        runtime_db = db_api.get_runtime(runtime_id)
        if runtime_db and runtime_db.status != status.AVAILABLE:
            raise exc.RuntimeNotAvailableException(
                'Runtime %s is not available.' % func_db.runtime_id
            )

    if version > 0:
        if func_db.code['source'] != constants.PACKAGE_FUNCTION:
            raise exc.InputException(
                "Can not specify version for %s type function." %
                constants.PACKAGE_FUNCTION
            )

        # update version count
        version_db = db_api.get_function_version(function_id, version)
        pre_version_count = version_db.count
        _update_function_version_db(version_db.id, pre_version_count)
    else:
        pre_count = func_db.count
        _update_function_db(function_id, pre_count)

    # input in params should be a string.
    if input:
        try:
            function_input = jsonutils.loads(input)
            # If input is e.g. '6', result of jsonutils.loads is 6 which can
            # not be stored in db.
            if type(function_input) == int:
                raise ValueError
            params['input'] = function_input
        except ValueError:
            params['input'] = {'__function_input': input}

    params.update({'status': status.RUNNING})
    db_model = db_api.create_execution(params)

    try:
        engine_client.create_execution(
            db_model.id, function_id, version, runtime_id,
            input=params.get('input'), is_sync=is_sync
        )
    except exc.QinlingException:
        # Catch RPC errors for executions:
        #   - for RemoteError in an RPC call, the execution status would be
        #     handled in the engine side;
        #   - for other exceptions in an RPC call or cast, the execution status
        #     would remain RUNNING so we should update it.
        db_model = db_api.get_execution(db_model.id)
        if db_model.status == status.RUNNING:
            db_model = db_api.update_execution(db_model.id,
                                               {'status': status.ERROR})
        return db_model

    if is_sync:
        # The execution should already be updated by engine service for sync
        # execution.
        db_model = db_api.get_execution(db_model.id)

    return db_model
