# Copyright 2017 - Catalyst IT Limited
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

import eventlet
eventlet.monkey_patch()

import sys

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import service

from qinling.api import service as api_service
from qinling import config
from qinling import rpc
from qinling.utils import common

CONF = cfg.CONF


def main():
    try:
        config.parse_args(args=common.get_properly_ordered_parameters())
        common.print_server_info("api")
        logging.setup(CONF, 'qinling')
        # Initialize RPC configuration.
        rpc.get_transport()

        api_server = api_service.WSGIService()
        launcher = service.launch(CONF, api_server, workers=api_server.workers,
                                  restart_method='mutate')
        launcher.wait()
    except RuntimeError as excp:
        sys.stderr.write("ERROR: %s\n" % excp)
        sys.exit(1)


if __name__ == '__main__':
    main()
