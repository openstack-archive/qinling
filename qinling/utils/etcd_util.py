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

import uuid

import etcd3gw
from oslo_config import cfg

CONF = cfg.CONF
CLIENT = None


def get_client(conf=None):
    global CLIENT
    conf = conf or CONF

    if not CLIENT:
        CLIENT = etcd3gw.client(host=conf.etcd.host, port=conf.etcd.port)

    return CLIENT


def get_worker_lock():
    client = get_client()
    return client.lock(id='function_worker')


def create_worker(function_id, worker):
    client = get_client()
    client.create(
        '%s/worker_%s' % (function_id, str(uuid.uuid4())),
        worker
    )


def get_workers(function_id, conf=None):
    client = get_client(conf)
    values = client.get_prefix('%s/worker' % function_id)
    workers = [w[0] for w in values]
    return workers


def delete_function(function_id):
    client = get_client()
    client.delete_prefix(function_id)


def create_service_url(function_id, url):
    client = get_client()
    client.create('%s/service_url' % function_id, url)


def get_service_url(function_id):
    client = get_client()
    return client.get('%s/service_url' % function_id)[0]
