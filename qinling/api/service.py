# Copyright 2017 Catalyst IT Limited
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_concurrency import processutils
from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import service
from oslo_service import wsgi

from qinling.api import app

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class WSGIService(service.ServiceBase):
    """Provides ability to launch Qinling API from wsgi app."""

    def __init__(self):
        self.app = app.setup_app()

        self.workers = CONF.api.api_workers
        if self.workers is not None and self.workers < 1:
            LOG.warning(
                "Value of config option api_workers must be integer "
                "greater than 1.  Input value ignored."
            )
            self.workers = None
        self.workers = self.workers or processutils.get_worker_count()

        self.server = wsgi.Server(
            cfg.CONF,
            "qinling_api",
            self.app,
            host=cfg.CONF.api.host,
            port=cfg.CONF.api.port,
            use_ssl=cfg.CONF.api.enable_ssl_api
        )

    def start(self):
        self.server.start()

    def stop(self):
        self.server.stop()

    def wait(self):
        self.server.wait()

    def reset(self):
        self.server.reset()
