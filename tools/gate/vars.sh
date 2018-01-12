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

# Set work dir if not already done
: ${WORK_DIR:="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"}

# Set logs directory
export LOGS_DIR=${LOGS_DIR:-"${WORK_DIR}/logs"}

# Get Host OS
source /etc/os-release
export HOST_OS=${HOST_OS:="${ID}"}

# Set versions of K8s to use
export KUBE_VERSION=${KUBE_VERSION:-"v1.7.3"}
export KUBEADM_IMAGE_VERSION=${KUBEADM_IMAGE_VERSION:-"v1.7.3"}

# Set K8s-AIO options
export KUBECONFIG=${KUBECONFIG:="${HOME}/.kubeadm-aio/admin.conf"}
export KUBEADM_IMAGE=${KUBEADM_IMAGE:="openstackhelm/kubeadm-aio:${KUBEADM_IMAGE_VERSION}"}

# Set K8s network options
export CNI_POD_CIDR=${CNI_POD_CIDR:="192.168.0.0/16"}
export KUBE_CNI=${KUBE_CNI:="calico"}

# Set Upstream DNS
export UPSTREAM_DNS=${UPSTREAM_DNS:-"8.8.8.8"}

# Set gate script timeouts
export SERVICE_LAUNCH_TIMEOUT=${SERVICE_LAUNCH_TIMEOUT:="600"}
export SERVICE_TEST_TIMEOUT=${SERVICE_TEST_TIMEOUT:="600"}
