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

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_service import service

from qinling.db import api as db_api
from qinling.engine import default_engine as engine
from qinling.engine import rpc

LOG = logging.getLogger(__name__)


class EngineService(service.Service):
    def __init__(self):
        super(EngineService, self).__init__()

        self.server = None

    def start(self):
        topic = cfg.CONF.engine.topic
        server = cfg.CONF.engine.host
        transport = messaging.get_transport(cfg.CONF)
        target = messaging.Target(topic=topic, server=server, fanout=False)
        endpoints = [engine.DefaultEngine()]
        self.server = messaging.get_rpc_server(
            transport,
            target,
            endpoints,
            executor='eventlet',
            serializer=rpc.ContextSerializer(
                messaging.serializer.JsonPayloadSerializer())
        )

        db_api.setup_db()

        LOG.info('Starting engine...')
        self.server.start()

        super(EngineService, self).start()

    def stop(self, graceful=False):
        if self.server:
            LOG.info('Stopping engine...')
            self.server.stop()
            if graceful:
                LOG.info(
                    'Consumer successfully stopped.  Waiting for final '
                    'messages to be processed...'
                )
                self.server.wait()

        super(EngineService, self).stop(graceful=graceful)

    def reset(self):
        if self.server:
            self.server.reset()

        super(EngineService, self).reset()
