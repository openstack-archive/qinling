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

from datetime import datetime
from datetime import timedelta

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import threadgroup

from qinling import context
from qinling.db import api as db_api
from qinling import rpc

LOG = logging.getLogger(__name__)
CONF = cfg.CONF
_THREAD_GROUP = None


def handle_function_service_expiration(ctx, engine_client, orchestrator):
    context.set_ctx(ctx)

    delta = timedelta(seconds=CONF.engine.function_service_expiration)
    expiry_time = datetime.utcnow() - delta

    results = db_api.get_functions(
        fields=['id'],
        sort_keys=['updated_at'],
        insecure=True,
        updated_at={'lte': expiry_time}
    )

    expiry_ids = [ret.id for ret in results]

    if not expiry_ids:
        return

    mappings = db_api.get_function_service_mappings(
        function_id={'in': expiry_ids}
    )

    LOG.info('Found total expiry function mapping numbers: %s', len(mappings))

    with db_api.transaction():
        for m in mappings:
            LOG.info('Deleting service mapping for function %s', m.function_id)

            engine_client.delete_function(m.function_id)
            db_api.delete_function_service_mapping(m.function_id)


def start(orchestrator):
    global _THREAD_GROUP
    _THREAD_GROUP = threadgroup.ThreadGroup()

    engine_client = rpc.get_engine_client()

    _THREAD_GROUP.add_timer(
        300,
        handle_function_service_expiration,
        ctx=context.Context(),
        engine_client=engine_client,
        orchestrator=orchestrator
    )


def stop():
    global _THREAD_GROUP

    if _THREAD_GROUP:
        _THREAD_GROUP.stop()
