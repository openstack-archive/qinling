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

import etcd3gw
from oslo_config import cfg
from oslo_utils import encodeutils

CONF = cfg.CONF
CLIENT = None


def get_client(conf=None):
    global CLIENT
    conf = conf or CONF

    if not CLIENT:
        if conf.etcd.protocol == "https":
            CLIENT = etcd3gw.client(host=conf.etcd.host,
                                    port=conf.etcd.port,
                                    protocol=conf.etcd.protocol,
                                    ca_cert=conf.etcd.ca_cert,
                                    cert_cert=conf.etcd.cert_file,
                                    cert_key=conf.etcd.cert_key)
        else:
            CLIENT = etcd3gw.client(host=conf.etcd.host,
                                    port=conf.etcd.port,
                                    protocol=conf.etcd.protocol)

    return CLIENT


def get_worker_lock(function_id, version=0):
    client = get_client()
    lock_id = "function_worker_%s_%s" % (function_id, version)
    return client.lock(id=lock_id)


def get_function_version_lock(function_id):
    client = get_client()
    lock_id = "function_version_%s" % function_id
    return client.lock(id=lock_id)


def create_worker(function_id, worker, version=0):
    """Create the worker info in etcd.

    The worker parameter is assumed to be unique.
    """
    # NOTE(huntxu): for the kubernetes orchestrator, which is the only
    # available orchestrator at the moment, the value of the worker param
    # is the name of the pod so it is unique.
    client = get_client()
    client.create(
        '%s_%s/worker_%s' % (function_id, version, worker),
        worker
    )


def delete_worker(function_id, worker, version=0):
    client = get_client()
    client.delete('%s_%s/worker_%s' % (function_id, version, worker))


def get_workers(function_id, version=0):
    client = get_client()
    values = client.get_prefix("%s_%s/worker" % (function_id, version))
    workers = [encodeutils.safe_decode(w[0]) for w in values]
    return workers


def delete_function(function_id, version=0):
    client = get_client()
    client.delete_prefix("%s_%s" % (function_id, version))


def create_service_url(function_id, url, version=0):
    client = get_client()
    client.create('%s_%s/service_url' % (function_id, version), url)


def get_service_url(function_id, version=0):
    client = get_client()
    values = client.get('%s_%s/service_url' % (function_id, version))
    return None if not values else encodeutils.safe_decode(values[0])
