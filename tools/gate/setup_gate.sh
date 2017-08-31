#!/bin/bash
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
set -ex
export WORK_DIR=$(pwd)
source ${WORK_DIR}/tools/gate/vars.sh
source ${WORK_DIR}/tools/gate/funcs/common.sh
source ${WORK_DIR}/tools/gate/funcs/network.sh

# Setup the logging location: by default use the working dir as the root.
rm -rf ${LOGS_DIR} || true
mkdir -p ${LOGS_DIR}

function dump_logs () {
  ${WORK_DIR}/tools/gate/dump_logs.sh
}
trap 'dump_logs "$?"' ERR

# Do the basic node setup for running the gate
gate_base_setup

# We setup the network for pre kube here, to enable cluster restarts on
# development machines
net_resolv_pre_kube
net_hosts_pre_kube

# Setup the K8s Cluster
bash ${WORK_DIR}/tools/gate/kubeadm_aio.sh

# Starts a proxy to the Kubernetes API server in a screen session
sudo screen -S kube_proxy -X quit || true
sudo screen -dmS kube_proxy && screen -S kube_proxy -X screen -t kube_proxy
sudo screen -S kube_proxy -p kube_proxy -X stuff 'kubectl proxy --accept-hosts=".*" --address="0.0.0.0"\n'
