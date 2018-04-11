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
source ${WORK_DIR}/tools/gate/kubeadm/vars.sh
source ${WORK_DIR}/tools/gate/kubeadm/funcs/common.sh
source ${WORK_DIR}/tools/gate/kubeadm/funcs/network.sh

# Do the basic node setup for running the gate
gate_base_setup
net_resolv_pre_kube
net_hosts_pre_kube

# Setup the K8s Cluster
ansible-playbook ${WORK_DIR}/tools/gate/kubeadm/playbook/deploy_k8s.yaml

# waits until kubectl can access the api server
mkdir -p ${HOME}/.kube
sudo cp /etc/kubernetes/admin.conf ${HOME}/.kube/config
sudo chown $(id -u):$(id -g) ${HOME}/.kube/config
end=$(($(date +%s) + 600))
READY="False"
while true; do
  READY=$(kubectl get nodes --no-headers=true | awk "{ print \$2 }" | head -1)
  [ "$READY" == "Ready" ] && break || true
  sleep 2
  now=$(date +%s)
  [ $now -gt $end ] && echo "Failed to setup kubernetes cluster in time" && exit -1
done

if [ "$QINLING_K8S_APISERVER_TLS" != "True" ]; then
  # Kubernetes proxy is needed if we don't use secure connections.
  create_k8s_screen
fi

#net_hosts_post_kube
#net_resolv_post_kube
