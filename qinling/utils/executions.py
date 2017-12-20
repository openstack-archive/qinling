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
import json

from oslo_log import log as logging

from qinling.db import api as db_api
from qinling.db.sqlalchemy import models
from qinling import exceptions as exc
from qinling import status

LOG = logging.getLogger(__name__)


def _update_function_db(function_id):
    with db_api.transaction():
        # NOTE(kong): Store function info in cache?
        func_db = db_api.get_function(function_id)
        runtime_db = func_db.runtime
        if runtime_db and runtime_db.status != status.AVAILABLE:
            raise exc.RuntimeNotAvailableException(
                'Runtime %s is not available.' % func_db.runtime_id
            )

    # Function update is done using UPDATE ... FROM ... WHERE
    # non-locking clause.
    while func_db:
        count = func_db.count
        modified = db_api.conditional_update(
            models.Function,
            {
                'count': count + 1,
            },
            {
                'id': function_id,
                'count': count
            },
            insecure=True,
        )
        if not modified:
            LOG.warning("Retrying to update function count.")
            func_db = db_api.get_function(function_id)
            continue
        else:
            break

    return func_db.runtime_id


def create_execution(engine_client, params):
    function_id = params['function_id']
    is_sync = params.get('sync', True)
    input = params.get('input')

    # input in params should be a string.
    if input:
        try:
            params['input'] = json.loads(input)
        except ValueError:
            params['input'] = {'__function_input': input}

    runtime_id = _update_function_db(function_id)

    params.update({'status': status.RUNNING})
    db_model = db_api.create_execution(params)

    engine_client.create_execution(
        db_model.id, function_id, runtime_id,
        input=params.get('input'), is_sync=is_sync
    )

    if is_sync:
        # The execution should already be updated by engine service for sync
        # execution.
        db_model = db_api.get_execution(db_model.id)

    return db_model
