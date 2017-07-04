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

import sys

import eventlet

eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)

import os

# If ../qinling/__init__.py exists, add ../ to Python search path, so that
# it will override what happens to be installed in /usr/(local/)lib/python...
POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir,
                                                os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'qinling', '__init__.py')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import service

from qinling.api import service as api_service
from qinling import config
from qinling.engine import service as eng_service
from qinling import rpc
from qinling import version

CONF = cfg.CONF


def launch_api():
    server = api_service.WSGIService('qinling_api')
    launcher = service.launch(CONF, server, workers=server.workers)
    launcher.wait()


def launch_engine():
    try:
        server = eng_service.EngineService()
        launcher = service.launch(CONF, server)
        launcher.wait()
    except RuntimeError as e:
        sys.stderr.write("ERROR: %s\n" % e)
        sys.exit(1)


def launch_any(options):
    # Launch the servers on different threads.
    threads = [eventlet.spawn(LAUNCH_OPTIONS[option])
               for option in options]

    [thread.wait() for thread in threads]


LAUNCH_OPTIONS = {
    'api': launch_api,
    'engine': launch_engine
}

QINLING_TITLE = r"""
                                /^L_      ,."\
           /~\       __       /~    \   ./    \
          /   _\   _/  \     /T~\|~\_\ / \_  /~|          _^
        / \ /W  \ / V^\/X  /~         T  . \/   \    ,v-./
 ,'`-. /~   ^     H  ,  . \/    ;   .   \      `. \-'   /
     M      ~     | . ;  /         ,  _   :  .    ~\_,-'
    /    ~    .    \    /   :                   '   \   ,/`
   I o. ^    oP     '98b         -      _  9.`       `\9b.
 8oO888.  oO888P  d888b9bo. .8o 888o.       8bo.  o     988o.
 88888888888888888888888888bo.98888888bo.    98888bo. .d888P
 88888888888888888888888888888888888888888888888888888888888
                     _          __   _
             ___ _  (_)  ___   / /  (_)  ___   ___ _
            / _ `/ / /  / _ \ / /  / /  / _ \ / _ `/
            \_, / /_/  /_//_//_/  /_/  /_//_/ \_, /
             /_/                             /___/

Function as a Service in OpenStack, version: %s
""" % version.version_string()


def print_server_info():
    print(QINLING_TITLE)

    comp_str = ("[%s]" % ','.join(LAUNCH_OPTIONS)
                if cfg.CONF.server == ['all'] else cfg.CONF.server)

    print('Launching server components %s...' % comp_str)


def get_properly_ordered_parameters():
    """Orders launch parameters in the right order.

    In oslo it's important the order of the launch parameters.
    if --config-file came after the command line parameters the command
    line parameters are ignored.
    So to make user command line parameters are never ignored this method
    moves --config-file to be always first.
    """
    args = sys.argv[1:]

    for arg in sys.argv[1:]:
        if arg == '--config-file' or arg.startswith('--config-file='):
            if "=" in arg:
                conf_file_value = arg.split("=", 1)[1]
            else:
                conf_file_value = args[args.index(arg) + 1]
                args.remove(conf_file_value)
            args.remove(arg)
            args.insert(0, "--config-file")
            args.insert(1, conf_file_value)

    return args


def main():
    try:
        config.parse_args(get_properly_ordered_parameters())
        print_server_info()

        logging.setup(CONF, 'Qinling')

        # Initialize RPC configuration.
        rpc.get_transport()

        if cfg.CONF.server == ['all']:
            launch_any(LAUNCH_OPTIONS.keys())
        else:
            if set(cfg.CONF.server) - set(LAUNCH_OPTIONS.keys()):
                raise Exception('Valid options are all or any combination of '
                                ', '.join(LAUNCH_OPTIONS.keys()))

            launch_any(set(cfg.CONF.server))

    except RuntimeError as excp:
        sys.stderr.write("ERROR: %s\n" % excp)
        sys.exit(1)


if __name__ == '__main__':
    sys.exit(main())
