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
import requests

from qinling.db import api as db_api
from qinling import exceptions as exc
from qinling import status

LOG = logging.getLogger(__name__)


def create_execution(engine_client, execution):
    function_id = execution['function_id']
    is_sync = execution.get('sync', True)
    func_url = None

    with db_api.transaction():
        func_db = db_api.get_function(function_id)
        # Increase function invoke count, the updated_at field will be also
        # updated.
        func_db.count = func_db.count + 1

        try:
            # Check if the service url is existing.
            mapping_db = db_api.get_function_service_mapping(function_id)
            LOG.info('Found Service url for function: %s', function_id)

            func_url = '%s/execute' % mapping_db.service_url
            LOG.info('Invoke function %s, url: %s', function_id, func_url)
        except exc.DBEntityNotFoundError:
            pass

        if func_url:
            r = requests.post(func_url, json=execution.get('input'))
            execution.update(
                {'status': 'success', 'output': {'result': r.json()}}
            )
        else:
            runtime_id = func_db.runtime_id
            runtime_db = db_api.get_runtime(runtime_id)
            if runtime_db.status != status.AVAILABLE:
                raise exc.RuntimeNotAvailableException(
                    'Runtime %s is not available.' % runtime_id
                )

            execution.update({'status': status.RUNNING})

        db_model = db_api.create_execution(execution)

    if not func_url:
        engine_client.create_execution(
            db_model.id, function_id, runtime_id,
            input=execution.get('input'),
            is_sync=is_sync
        )

    return db_model
