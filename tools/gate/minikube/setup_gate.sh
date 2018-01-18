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

# Do the basic node setup for running the gate
gate_base_setup
net_resolv_pre_kube
net_hosts_pre_kube

# Setup the K8s Cluster
source ${WORK_DIR}/tools/gate/minikube/setup_minikube.sh
create_k8s_screen

#net_hosts_post_kube
#net_resolv_post_kube