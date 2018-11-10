#!/usr/bin/env bash
# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace


function install_qinling {
    git_clone $QINLING_REPO $QINLING_DIR $QINLING_BRANCH
    setup_develop $QINLING_DIR
}


function install_qinlingclient {
    if use_library_from_git "python-qinlingclient"; then
        git_clone $QINLINGCLIENT_REPO $QINLINGCLIENT_DIR $QINLINGCLIENT_BRANCH
        setup_develop $QINLINGCLIENT_DIR
    else
        pip_install python-qinlingclient
    fi
}


function install_k8s {
    pushd $QINLING_DIR
    source tools/gate/kubeadm/setup_gate.sh
    popd

    # Pre-fetch the docker images for runtimes and image function test.
    for image in "$QINLING_PYTHON_RUNTIME_IMAGE" "$QINLING_NODEJS_RUNTIME_IMAGE" "$QINLING_SIDECAR_IMAGE" "openstackqinling/alpine-test" "lingxiankong/sleep"
    do
        sudo docker pull $image
    done
}


function create_qinling_accounts {
    create_service_user "qinling" "admin"

    local qinling_service=$(get_or_create_service "qinling" "function-engine" "Function Service")
    qinling_api_url="$QINLING_SERVICE_PROTOCOL://$QINLING_SERVICE_HOST:$QINLING_SERVICE_PORT"

    get_or_create_endpoint $qinling_service \
        "$REGION_NAME" \
        "$qinling_api_url" \
        "$qinling_api_url" \
        "$qinling_api_url"

    # get or adds 'service' role to 'qinling' user on 'demo' project
    get_or_add_user_project_role "service" "qinling" "demo"
}


function mkdir_chown_stack {
    if [[ ! -d "$1" ]]; then
        sudo mkdir -p "$1"
    fi
    sudo chown -R $STACK_USER:$STACK_USER "$1"
}


function configure_k8s_certificates {
    pushd $QINLING_DIR

    mkdir_chown_stack "$QINLING_CONF_DIR"/pki
    mkdir_chown_stack "$QINLING_CONF_DIR"/pki/kubernetes

    curl -L https://pkg.cfssl.org/R1.2/cfssl_linux-amd64 -o /tmp/cfssl
    chmod +x /tmp/cfssl
    curl -L https://pkg.cfssl.org/R1.2/cfssljson_linux-amd64 -o /tmp/cfssljson
    chmod +x /tmp/cfssljson

    sudo /tmp/cfssl gencert -ca=/etc/kubernetes/pki/ca.crt -ca-key=/etc/kubernetes/pki/ca.key -config=example/kubernetes/cfssl-ca-config.json -profile=client example/kubernetes/cfssl-client-csr.json | /tmp/cfssljson -bare client
    # The command above outputs client-key.pem, client.pem and client.csr
    mv client-key.pem "$QINLING_CONF_DIR"/pki/kubernetes/qinling.key
    mv client.pem "$QINLING_CONF_DIR"/pki/kubernetes/qinling.crt
    rm -f client.csr

    cp /etc/kubernetes/pki/ca.crt "$QINLING_CONF_DIR"/pki/kubernetes/ca.crt

    popd
}

function configure_etcd_certificates {
    pushd $QINLING_DIR

    mkdir_chown_stack $QINLING_CONF_DIR/pki/etcd
    sudo cp /etc/kubernetes/pki/etcd/ca.crt $QINLING_CONF_DIR/pki/etcd/

    # Re-use k8s api server etcd client cert
    sudo cp /etc/kubernetes/pki/apiserver-etcd-client.crt $QINLING_CONF_DIR/pki/etcd/qinling-etcd-client.crt
    sudo cp /etc/kubernetes/pki/apiserver-etcd-client.key $QINLING_CONF_DIR/pki/etcd/qinling-etcd-client.key

    mkdir_chown_stack $QINLING_CONF_DIR/pki/etcd
    # For the tempest user to read the key file when running tempest
    chmod 644 $QINLING_CONF_DIR/pki/etcd/qinling-etcd-client.key

    popd
}


function configure_qinling {
    mkdir_chown_stack "$QINLING_AUTH_CACHE_DIR"
    rm -rf "$QINLING_AUTH_CACHE_DIR"/*

    mkdir_chown_stack "$QINLING_CONF_DIR"
    rm -rf "$QINLING_CONF_DIR"/*

    mkdir_chown_stack "$QINLING_FUNCTION_STORAGE_DIR"
    rm -rf "$QINLING_FUNCTION_STORAGE_DIR"/*

    cp $QINLING_DIR/etc/policy.json.sample $QINLING_POLICY_FILE

    # Generate Qinling configuration file and configure common parameters.
    oslo-config-generator --config-file $QINLING_DIR/tools/config/config-generator.qinling.conf --output-file $QINLING_CONF_FILE

    iniset $QINLING_CONF_FILE oslo_policy policy_file $QINLING_POLICY_FILE
    iniset $QINLING_CONF_FILE DEFAULT debug $QINLING_DEBUG
    iniset $QINLING_CONF_FILE DEFAULT server all
    iniset $QINLING_CONF_FILE DEFAULT logging_context_format_string "%(asctime)s %(process)d %(color)s %(levelname)s [%(request_id)s] %(message)s %(resource)s (%(name)s)"
    iniset $QINLING_CONF_FILE storage file_system_dir $QINLING_FUNCTION_STORAGE_DIR

    # Setup keystone_authtoken section
    configure_auth_token_middleware $QINLING_CONF_FILE qinling $QINLING_AUTH_CACHE_DIR
    iniset $QINLING_CONF_FILE keystone_authtoken www_authenticate_uri $KEYSTONE_AUTH_URI_V3
    iniset $QINLING_CONF_FILE keystone_authtoken region_name "$REGION_NAME"

    # Setup RabbitMQ credentials
    iniset_rpc_backend qinling $QINLING_CONF_FILE

    # Configure the database.
    iniset $QINLING_CONF_FILE database connection `database_connection_url qinling`

    if [ "$QINLING_INSTALL_K8S" == "True" ]; then
        # Configure Kubernetes API server certificates for qinling if required.
        if [ "$QINLING_K8S_APISERVER_TLS" == "True" ]; then
            iniset $QINLING_CONF_FILE kubernetes kube_host https://$(hostname -f):6443
            configure_k8s_certificates
            sudo kubectl create -f $QINLING_DIR/example/kubernetes/k8s_qinling_role.yaml
        else
            iniset $QINLING_CONF_FILE kubernetes use_api_certificate False
        fi

        # Config etcd TLS certs
        configure_etcd_certificates
    else
        echo_summary "Skip k8s related configuration"
    fi

    iniset $QINLING_CONF_FILE kubernetes replicas 5

    if [ -n ${QINLING_TRUSTED_CIDRS} ]; then
        iniset $QINLING_CONF_FILE kubernetes trusted_cidrs ${QINLING_TRUSTED_CIDRS}
    else
        iniset $QINLING_CONF_FILE kubernetes trusted_cidrs "${HOST_IP}/32,127.0.0.1/32"
    fi
}


function init_qinling {
    # (re)create qinling database
    recreate_database qinling utf8

    $QINLING_BIN_DIR/qinling-db-manage --config-file $QINLING_CONF_FILE upgrade head
}


function start_qinling {
    run_process qinling-engine "$QINLING_BIN_DIR/qinling-engine --config-file $QINLING_CONF_FILE"
    run_process qinling-api "$QINLING_BIN_DIR/qinling-api --config-file $QINLING_CONF_FILE"
}


function stop_qinling {
    local serv
    for serv in qinling-api qinling-engine; do
        stop_process $serv
    done
}


function cleanup_qinling {
    sudo rm -rf $QINLING_AUTH_CACHE_DIR/*
    sudo rm -rf $QINLING_CONF_DIR/*
}


# check for service enabled
if is_service_enabled qinling; then
    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        # Perform installation of service source
        echo_summary "Installing qinling"
        install_qinling
        echo_summary "Installing qinlingclient"
        install_qinlingclient

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        # Configure after the other layer 1 and 2 services have been configured
        echo_summary "Configuring qinling"
        if is_service_enabled key; then
            create_qinling_accounts
        fi

        if [ "$QINLING_INSTALL_K8S" == "True" ]; then
            echo_summary "Installing kubernetes cluster"
            install_k8s
        else
            echo_summary "Skip kubernetes cluster installation"
        fi

        configure_qinling

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize and start the qinling service
        echo_summary "Initializing qinling"
        init_qinling
        start_qinling
    fi

    if [[ "$1" == "unstack" ]]; then
        echo_summary "Shutting down qinling"
        stop_qinling
    fi

    if [[ "$1" == "clean" ]]; then
        echo_summary "Cleaning qinling"
        cleanup_qinling
    fi
fi


# Restore xtrace
$XTRACE
