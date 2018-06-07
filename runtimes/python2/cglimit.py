# Copyright 2018 Catalyst IT Limited
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

import logging
import os
import sys

from flask import Flask
from flask import make_response
from flask import request
from oslo_concurrency import lockutils

app = Flask(__name__)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
del app.logger.handlers[:]
app.logger.addHandler(ch)

# Deployer can specify cfs_period_us default value here.
PERIOD = 100000


def log(message, level="info"):
    global app
    log_func = getattr(app.logger, level)
    log_func(message)


@lockutils.synchronized('set_limitation', external=True,
                        lock_path='/var/lock/qinling')
def _cgroup_limit(cpu, memory_size, pid):
    """Modify 'cgroup' files to set resource limits.

    Each pod(worker) will have cgroup folders on the host cgroup filesystem,
    like '/sys/fs/cgroup/<resource_type>/kubepods/<qos_class>/pod<pod_id>/',
    to limit memory and cpu resources that can be used in pod.

    For more information about cgroup, please see [1], about sharing PID
    namespaces in kubernetes, please see also [2].

    Return None if successful otherwise a Flask.Response object.

    [1]https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/6/html/resource_management_guide/sec-creating_cgroups
    [2]https://github.com/kubernetes/kubernetes/pull/51634
    """
    hostname = os.getenv('HOSTNAME')
    pod_id = os.getenv('POD_UID')
    qos_class = None
    if os.getenv('QOS_CLASS') == 'BestEffort':
        qos_class = 'besteffort'
    elif os.getenv('QOS_CLASS') == 'Burstable':
        qos_class = 'burstable'
    elif os.getenv('QOS_CLASS') == 'Guaranteed':
        qos_class = ''

    if not pod_id or qos_class is None:
        return make_response("Failed to get current worker information", 500)

    memory_base_path = os.path.join('/qinling_cgroup', 'memory', 'kubepods',
                                    qos_class, 'pod%s' % pod_id)
    cpu_base_path = os.path.join('/qinling_cgroup', 'cpu', 'kubepods',
                                 qos_class, 'pod%s' % pod_id)
    memory_path = os.path.join(memory_base_path, hostname)
    cpu_path = os.path.join(cpu_base_path, hostname)

    if os.path.isdir(memory_base_path):
        if not os.path.isdir(memory_path):
            os.makedirs(memory_path)

    if os.path.isdir(cpu_base_path):
        if not os.path.isdir(cpu_path):
            os.makedirs(cpu_path)

    try:
        # set cpu and memory resource limits
        with open('%s/memory.limit_in_bytes' % memory_path, 'w') as f:
            f.write('%d' % int(memory_size))
        with open('%s/cpu.cfs_period_us' % cpu_path, 'w') as f:
            f.write('%d' % PERIOD)
        with open('%s/cpu.cfs_quota_us' % cpu_path, 'w') as f:
            f.write('%d' % ((int(cpu)*PERIOD/1000)))

        # add pid to 'tasks' files
        with open('%s/tasks' % memory_path, 'w') as f:
            f.write('%d' % pid)
        with open('%s/tasks' % cpu_path, 'w') as f:
            f.write('%d' % pid)
    except Exception as e:
        return make_response("Failed to modify cgroup files: %s"
                             % str(e), 500)


@app.route('/cglimit', methods=['POST'])
def cglimit():
    """Set resource limitations for execution.

    Only root user has jurisdiction to modify all cgroup files.

    :param cpu: cpu resource that execution can use in total.
    :param memory_size: RAM resource that execution can use in total.

    Currently swap ought to be disabled in kubernetes.
    """
    params = request.get_json()
    cpu = params['cpu']
    memory_size = params['memory_size']
    pid = params['pid']
    log("Set resource limits request received, params: %s" % params)

    resp = _cgroup_limit(cpu, memory_size, pid)

    return resp if resp else 'pidlimited'
