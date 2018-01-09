#!/usr/bin/env bash
set -xe

sudo apt-get install -y --no-install-recommends -qq \
        docker.io \
        jq

curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 && sudo chmod +x minikube
curl -Lo kubectl https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl && sudo chmod +x kubectl && sudo mv ./kubectl /usr/local/bin/kubectl

export MINIKUBE_WANTUPDATENOTIFICATION=false
export MINIKUBE_WANTREPORTERRORPROMPT=false
export MINIKUBE_HOME=$HOME
export CHANGE_MINIKUBE_NONE_USER=true
mkdir $HOME/.kube || true
touch $HOME/.kube/config

export KUBECONFIG=$HOME/.kube/config
sudo ./minikube delete || true
sudo -E ./minikube start --vm-driver=none --kubernetes-version ${KUBE_VERSION} --loglevel 0

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
