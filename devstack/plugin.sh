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
    source tools/gate/setup_gate.sh
    popd

    # Pre-pull the default docker image for python runtime
    sudo docker pull $QINLING_PYTHON_RUNTIME_IMAGE
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
    sudo chown $STACK_USER "$1"
}


function configure_qinling {
    mkdir_chown_stack "$QINLING_AUTH_CACHE_DIR"
    rm -f "$QINLING_AUTH_CACHE_DIR"/*

    mkdir_chown_stack "$QINLING_CONF_DIR"
    rm -f "$QINLING_CONF_DIR"/*

    mkdir_chown_stack "$QINLING_FUNCTION_STORAGE_DIR"
    rm -f "$QINLING_FUNCTION_STORAGE_DIR"/*

    # Generate Qinling configuration file and configure common parameters.
    oslo-config-generator --config-file $QINLING_DIR/tools/config/config-generator.qinling.conf --output-file $QINLING_CONF_FILE

    iniset $QINLING_CONF_FILE DEFAULT debug $QINLING_DEBUG
    iniset $QINLING_CONF_FILE DEFAULT server all
    iniset $QINLING_CONF_FILE storage file_system_dir $QINLING_FUNCTION_STORAGE_DIR
    iniset $QINLING_CONF_FILE kubernetes qinling_service_address $DEFAULT_HOST_IP

    # Setup keystone_authtoken section
    configure_auth_token_middleware $QINLING_CONF_FILE qinling $QINLING_AUTH_CACHE_DIR
    iniset $QINLING_CONF_FILE keystone_authtoken auth_uri $KEYSTONE_AUTH_URI_V3

    # Setup RabbitMQ credentials
    iniset_rpc_backend qinling $QINLING_CONF_FILE

    # Configure the database.
    iniset $QINLING_CONF_FILE database connection `database_connection_url qinling`
}


function init_qinling {
    # (re)create qinling database
    recreate_database qinling utf8

    $QINLING_BIN_DIR/qinling-db-manage --config-file $QINLING_CONF_FILE upgrade head
}


function start_qinling {
    run_process qinling-engine "$QINLING_BIN_DIR/qinling-server --server engine --config-file $QINLING_CONF_FILE"
    run_process qinling-api "$QINLING_BIN_DIR/qinling-server --server api --config-file $QINLING_CONF_FILE"
}


function stop_qingling {
    local serv
    for serv in qinling-api qingling-engine; do
        stop_process $serv
    done
}


function cleanup_qingling {
    sudo rm -rf $QINLING_AUTH_CACHE_DIR
    sudo rm -rf $QINLING_CONF_DIR
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

        echo_summary "Installing kubernetes cluster"
        install_k8s

        configure_qinling

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize and start the qinling service
        echo_summary "Initializing qinling"
        init_qinling
        start_qinling
    fi

    if [[ "$1" == "unstack" ]]; then
        echo_summary "Shutting down qingling"
        stop_qingling
    fi

    if [[ "$1" == "clean" ]]; then
        echo_summary "Cleaning qingling"
        cleanup_qingling
    fi
fi


# Restore xtrace
$XTRACE
