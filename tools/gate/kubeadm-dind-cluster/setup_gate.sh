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

function net_default_iface {
 sudo ip -4 route list 0/0 | awk '{ print $5; exit }'
}

function net_default_host_addr {
 sudo ip addr | awk "/inet / && /$(net_default_iface)/{print \$2; exit }"
}

function net_default_host_ip {
 echo $(net_default_host_addr) | awk -F '/' '{ print $1; exit }'
}

function net_hosts_pre_kube {
  sudo cp -f /etc/hosts /etc/hosts-pre-kube
  sudo sed -i "/$(hostname)/d" /etc/hosts
  sudo sed -i "/127.0.0.1/d" /etc/hosts
  sudo sed -i "1 i 127.0.0.1 localhost" /etc/hosts

  host_ip=$(net_default_host_ip)
  echo "${host_ip} $(hostname)" | sudo tee -a /etc/hosts
}

function create_k8s_screen {
  # Starts a proxy to the Kubernetes API server in a screen session
  sudo screen -S kube_proxy -X quit || true
  sudo screen -dmS kube_proxy && sudo screen -S kube_proxy -X screen -t kube_proxy
  sudo screen -S kube_proxy -p kube_proxy -X stuff 'kubectl proxy --accept-hosts=".*" --address="0.0.0.0"\n'
}

function tweak_etcd {
  ETCD_VER=v3.2.0
  TMP_DIR=/tmp/etcd
  sudo rm -rf $TMP_DIR && mkdir -p $TMP_DIR
  curl -L https://github.com/coreos/etcd/releases/download/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz \
    -o /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
  tar xzvf /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz -C $TMP_DIR --strip-components=1

  # Stop etcd service installed by apt
  sudo systemctl stop etcd
  cp $TMP_DIR/etcd /usr/bin/etcd
  cp $TMP_DIR/etcdctl /usr/bin/etcdctl
  sudo systemctl start etcd
}


sudo apt-get update -y
sudo apt-get install -y --no-install-recommends -qq \
        docker.io \
        jq \
        screen \
        etcd

net_hosts_pre_kube

curl -sSO https://cdn.rawgit.com/Mirantis/kubeadm-dind-cluster/master/fixed/dind-cluster-v1.8.sh
sudo chmod +x dind-cluster-v1.8.sh
sudo ./dind-cluster-v1.8.sh clean || true
sudo ./dind-cluster-v1.8.sh up
echo 'export PATH="$HOME/.kubeadm-dind-cluster:$PATH"' >> $HOME/.bashrc

# Treak etcd service, the default etcd version installed by apt is v2, we need
# v3 instead.
tweak_etcd

# Starts a proxy to the Kubernetes API server in a screen session
create_k8s_screen
