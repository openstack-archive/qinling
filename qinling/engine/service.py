# Copyright 2017 Catalyst IT Limited
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import cotyledon
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_messaging.rpc import dispatcher

from qinling.db import api as db_api
from qinling.engine import default_engine as engine
from qinling.orchestrator import base as orchestra_base
from qinling import rpc
from qinling.services import periodics
from qinling.utils.openstack import keystone as keystone_utils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class EngineService(cotyledon.Service):
    def __init__(self, worker_id):
        super(EngineService, self).__init__(worker_id)
        self.server = None

    def run(self):
        qinling_endpoint = keystone_utils.get_qinling_endpoint()
        orchestrator = orchestra_base.load_orchestrator(CONF, qinling_endpoint)
        db_api.setup_db()

        topic = CONF.engine.topic
        server = CONF.engine.host
        transport = messaging.get_rpc_transport(CONF)
        target = messaging.Target(topic=topic, server=server, fanout=False)
        endpoint = engine.DefaultEngine(orchestrator, qinling_endpoint)
        access_policy = dispatcher.DefaultRPCAccessPolicy
        self.server = messaging.get_rpc_server(
            transport,
            target,
            [endpoint],
            executor='threading',
            access_policy=access_policy,
            serializer=rpc.ContextSerializer(
                messaging.serializer.JsonPayloadSerializer())
        )

        LOG.info('Starting function mapping periodic task...')
        periodics.start_function_mapping_handler(endpoint)

        LOG.info('Starting engine...')
        self.server.start()

    def terminate(self):
        periodics.stop()

        if self.server:
            LOG.info('Stopping engine...')
            self.server.stop()
            self.server.wait()
