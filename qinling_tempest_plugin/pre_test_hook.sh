#!/usr/bin/env bash
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# This script is executed inside pre_test_hook function in devstack gate.

set -ex

export localconf=$BASE/new/devstack/local.conf
export QINLING_CONF=/etc/qinling/qinling.conf

# Install k8s cluster
bash $BASE/new/qinling/tools/gate/setup_gate.sh

echo -e '[[post-config|$QINLING_CONF]]\n[kubernetes]\n' >> $localconf
echo -e 'qinling_service_address=${DEFAULT_HOST_IP}\n' >> $localconf
