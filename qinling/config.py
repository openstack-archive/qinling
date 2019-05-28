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
from keystoneauth1 import loading
from keystonemiddleware import auth_token
from oslo_concurrency import processutils
from oslo_config import cfg
from oslo_log import log
from oslo_middleware import cors

from qinling import version

CONF = cfg.CONF

launch_opt = cfg.ListOpt(
    'server',
    default=['all'],
    help='Specifies which qinling server to start by the launch script.'
)

default_opts = [
    cfg.StrOpt(
        'qinling_endpoint',
        help='Qinling service endpoint.'
    ),
]

API_GROUP = 'api'
api_opts = [
    cfg.StrOpt('host', default='0.0.0.0', help='Qinling API server host.'),
    cfg.PortOpt('port', default=7070, help='Qinling API server port.'),
    cfg.BoolOpt(
        'enable_ssl_api',
        default=False,
        help='Enable the integrated stand-alone API to service requests'
             'via HTTPS instead of HTTP.'
    ),
    cfg.IntOpt(
        'api_workers',
        default=processutils.get_worker_count(),
        help='Number of workers for Qinling API service '
             'default is equal to the number of CPUs available if that can '
             'be determined, else a default worker count of 1 is returned.'
    ),
    cfg.BoolOpt(
        'enable_job_handler',
        default=True,
        help='Enable job handler.'
    ),
]

PECAN_GROUP = 'pecan'
pecan_opts = [
    cfg.StrOpt(
        'root',
        default='qinling.api.controllers.root.RootController',
        help='Pecan root controller'
    ),
    cfg.ListOpt(
        'modules',
        default=["qinling.api"],
        help='A list of modules where pecan will search for applications.'
    ),
    cfg.BoolOpt(
        'debug',
        default=False,
        help='Enables the ability to display tracebacks in the browser and'
             ' interactively debug during development.'
    ),
    cfg.BoolOpt(
        'auth_enable',
        default=True,
        help='Enables user authentication in pecan.'
    )
]

ENGINE_GROUP = 'engine'
engine_opts = [
    cfg.StrOpt(
        'host',
        default='0.0.0.0',
        help='Name of the engine node. This can be an opaque '
             'identifier. It is not necessarily a hostname, '
             'FQDN, or IP address.'
    ),
    cfg.StrOpt(
        'topic',
        default='qinling_engine',
        help='The message topic that the engine listens on.'
    ),
    cfg.StrOpt(
        'orchestrator',
        default='kubernetes',
        choices=['kubernetes', 'swarm'],
        help='The container orchestrator.'
    ),
    cfg.IntOpt(
        'function_service_expiration',
        default=3600,
        help='Maximum service time in seconds for function in orchestrator.'
    ),
    cfg.IntOpt(
        'function_concurrency',
        default=3,
        help='Maximum number of concurrent executions per function.'
    ),
    cfg.StrOpt(
        'sidecar_image',
        default='openstackqinling/sidecar:0.0.2',
        help='The sidecar image being used together with the worker.'
    ),
]

STORAGE_GROUP = 'storage'
storage_opts = [
    cfg.StrOpt(
        'file_system_dir',
        help='Directory to store function packages.'
    ),
    cfg.StrOpt(
        'provider',
        default='local',
        choices=['local', 'swift'],
        help='Storage provider for function code package.'
    ),
]

KUBERNETES_GROUP = 'kubernetes'
kubernetes_opts = [
    cfg.StrOpt(
        'namespace',
        default='qinling',
        help='Resources scope created by Qinling.'
    ),
    cfg.IntOpt(
        'replicas',
        default=3,
        help='Number of desired replicas in deployment.'
    ),
    cfg.StrOpt(
        'kube_host',
        default='http://127.0.0.1:8001',
        help='Kubernetes server address, e.g. you can start a proxy to the '
             'Kubernetes API server by using "kubectl proxy" command.'
    ),
    cfg.BoolOpt(
        'use_api_certificate',
        default=True,
        help='Whether to use client certificates to connect to the '
             'Kubernetes API server.'
    ),
    cfg.StrOpt(
        'ssl_ca_cert',
        default='/etc/qinling/pki/kubernetes/ca.crt',
        help='Path to the CA certificate for qinling to use to connect to '
             'the Kubernetes API server.'
    ),
    cfg.StrOpt(
        'cert_file',
        default='/etc/qinling/pki/kubernetes/qinling.crt',
        help='Path to the client certificate for qinling to use to '
             'connect to the Kubernetes API server.'
    ),
    cfg.StrOpt(
        'key_file',
        default='/etc/qinling/pki/kubernetes/qinling.key',
        help='Path to the client certificate key file for qinling to use to '
             'connect to the Kubernetes API server.'
    ),
    cfg.StrOpt(
        'log_devel',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Log level for kubernetes operations.'
    ),
    cfg.ListOpt(
        'trusted_cidrs',
        deprecated_for_removal=True,
        item_type=cfg.types.String(),
        default=[],
        help='List of CIDR that have access to the services in '
             'Kubernetes, e.g. trusted_cidrs=127.0.0.1/32,198.72.124.109/32. '
             'If it is empty list, the default value is the host IP address '
             'that the qinling-engine service is running on.'
    )
]

ETCD_GROUP = 'etcd'
etcd_opts = [
    cfg.StrOpt(
        'host',
        default='127.0.0.1',
        help='Etcd service host address.'
    ),
    cfg.PortOpt(
        'port',
        default=2379,
        help='Etcd service port.'
    ),
    cfg.StrOpt(
        'protocol',
        default='https',
        choices=['http', 'https'],
        help='Etcd connection protocol.'
    ),
    cfg.StrOpt(
        'ca_cert',
        default='/etc/qinling/pki/etcd/ca.crt',
        help='Path to CA certificate file to use to securely '
             'connect to etcd server.'
    ),
    cfg.StrOpt(
        'cert_file',
        default='/etc/qinling/pki/etcd/qinling-etcd-client.crt',
        help='Path to client certificate file to use to securely '
             'connect to etcd server.'
    ),
    cfg.StrOpt(
        'cert_key',
        default='/etc/qinling/pki/etcd/qinling-etcd-client.key',
        help='Path to client certificate key file to use to securely '
             'connect to etcd server.'
    ),
]

RLIMITS_GROUP = 'resource_limits'
rlimits_opts = [
    cfg.IntOpt(
        'default_cpu',
        default=100,
        help='Default cpu resource(unit: millicpu).'
    ),
    cfg.IntOpt(
        'min_cpu',
        default=100,
        help='Minimum cpu resource(unit: millicpu).'
    ),
    cfg.IntOpt(
        'max_cpu',
        default=300,
        help='Maximum cpu resource(unit: millicpu).'
    ),
    cfg.IntOpt(
        'default_memory',
        default=33554432,
        help='Default memory resource(unit: bytes).'
    ),
    cfg.IntOpt(
        'min_memory',
        default=33554432,
        help='Minimum memory resource(unit: bytes).'
    ),
    cfg.IntOpt(
        'max_memory',
        default=134217728,
        help='Maximum memory resource(unit: bytes).'
    ),
    cfg.IntOpt(
        'default_timeout',
        default=5,
        help='Default function execution timeout(unit: seconds)'
    ),
    cfg.IntOpt(
        'min_timeout',
        default=1,
        help='Minimum function execution timeout(unit: seconds).'
    ),
    cfg.IntOpt(
        'max_timeout',
        default=300,
        help='Maximum function execution timeout(unit: seconds).'
    ),
]


def list_opts():
    keystone_middleware_opts = auth_token.list_opts()
    keystone_loading_opts = [(
        'keystone_authtoken', loading.get_auth_plugin_conf_options('password')
    )]

    qinling_opts = [
        (API_GROUP, api_opts),
        (PECAN_GROUP, pecan_opts),
        (ENGINE_GROUP, engine_opts),
        (STORAGE_GROUP, storage_opts),
        (KUBERNETES_GROUP, kubernetes_opts),
        (ETCD_GROUP, etcd_opts),
        (RLIMITS_GROUP, rlimits_opts),
        (None, [launch_opt]),
        (None, default_opts),
    ]

    return keystone_middleware_opts + keystone_loading_opts + qinling_opts


def parse_args(args=None, usage=None, default_config_files=None):
    CLI_OPTS = [launch_opt]
    CONF.register_cli_opts(CLI_OPTS)

    for group, options in list_opts():
        CONF.register_opts(list(options), group)

    _DEFAULT_LOG_LEVELS = [
        'eventlet.wsgi.server=WARN',
        'oslo_service.periodic_task=INFO',
        'oslo_service.loopingcall=INFO',
        'oslo_db=WARN',
        'oslo_concurrency.lockutils=WARN',
        'kubernetes.client.rest=%s' % CONF.kubernetes.log_devel,
        'keystoneclient=INFO',
        'requests.packages.urllib3.connectionpool=CRITICAL',
        'urllib3.connectionpool=CRITICAL',
        'cotyledon=INFO',
        'futurist.periodics=WARN'
    ]
    default_log_levels = log.get_default_log_levels()
    default_log_levels.extend(_DEFAULT_LOG_LEVELS)
    log.set_defaults(default_log_levels=default_log_levels)
    log.register_options(CONF)

    CONF(
        args=args,
        project='qinling',
        version=version,
        usage=usage,
        default_config_files=default_config_files
    )


def set_config_defaults():
    """This method updates all configuration default values."""
    set_cors_middleware_defaults()


def set_cors_middleware_defaults():
    """Update default configuration options for oslo.middleware."""
    cors.set_defaults(
        allow_headers=['X-Auth-Token',
                       'X-Identity-Status',
                       'X-Roles',
                       'X-Service-Catalog',
                       'X-User-Id',
                       'X-Tenant-Id',
                       'X-Project-Id',
                       'X-User-Name',
                       'X-Project-Name'],
        allow_methods=['GET',
                       'PUT',
                       'POST',
                       'DELETE',
                       'PATCH'],
        expose_headers=['X-Auth-Token',
                        'X-Subject-Token',
                        'X-Service-Token',
                        'X-Project-Id',
                        'X-User-Name',
                        'X-Project-Name']
    )
