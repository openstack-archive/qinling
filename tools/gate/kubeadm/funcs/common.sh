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

function base_install {
  if [ "x$HOST_OS" == "xubuntu" ]; then
    sudo apt-add-repository --yes ppa:ansible/ansible
    sudo apt-get update -y
    sudo apt-get install -y --no-install-recommends \
      iproute2 \
      iptables \
      ipcalc \
      nmap \
      lshw \
      screen \
      ansible
  elif [ "x$HOST_OS" == "xcentos" ]; then
    sudo yum install -y \
      epel-release
    # ipcalc is in the initscripts package
    sudo yum install -y \
      iproute \
      iptables \
      initscripts \
      nmap \
      lshw \
      screen \
      ansible
  elif [ "x$HOST_OS" == "xfedora" ]; then
    sudo dnf install -y \
      iproute \
      iptables \
      ipcalc \
      nmap \
      lshw \
      ansible
  fi
}

function gate_base_setup {
  # Install base requirements
  base_install
}

function create_k8s_screen {
  # Starts a proxy to the Kubernetes API server in a screen session
  sudo screen -S kube_proxy -X quit || true
  sudo screen -dmS kube_proxy
  sudo screen -S kube_proxy -p bash -X stuff 'kubectl proxy --accept-hosts=".*" --address="0.0.0.0"\n'
}