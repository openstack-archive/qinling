#!/usr/bin/env bash
set -xe

sudo apt-get install -y --no-install-recommends -qq jq

TMP_DIR=$(mktemp -d)

curl -sSL https://storage.googleapis.com/kubernetes-release/release/${KUBE_VERSION}/bin/linux/amd64/kubectl -o ${TMP_DIR}/kubectl
chmod +x ${TMP_DIR}/kubectl
sudo mv ${TMP_DIR}/kubectl /usr/local/bin/kubectl

curl -sSL https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 -o ${TMP_DIR}/minikube
chmod +x ${TMP_DIR}/minikube
sudo mv ${TMP_DIR}/minikube /usr/local/bin/minikube

curl -fsSL get.docker.com -o ${TMP_DIR}/get-docker.sh
sudo sh ${TMP_DIR}/get-docker.sh

rm -rf ${TMP_DIR}

export MINIKUBE_WANTUPDATENOTIFICATION=false
export MINIKUBE_WANTREPORTERRORPROMPT=false
export MINIKUBE_HOME=$HOME
export CHANGE_MINIKUBE_NONE_USER=true

rm -rf $HOME/.kube
mkdir $HOME/.kube || true
touch $HOME/.kube/config

export KUBECONFIG=$HOME/.kube/config
sudo minikube delete || true
sudo -E minikube start --vm-driver=none --kubernetes-version ${KUBE_VERSION} --loglevel 0

# waits until kubectl can access the api server that Minikube has created
end=$(($(date +%s) + 600))
READY="False"
while true; do
  kubectl get po &> /dev/null
  if [ $? -ne 1 ]; then
    READY="True"
    echo "Kubernetes cluster is ready!"
  fi
  [ $READY == "True" ] && break || true
  sleep 2
  now=$(date +%s)
  [ $now -gt $end ] && echo "Failed to setup kubernetes cluster in time" && exit -1
done
