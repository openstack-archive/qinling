#!/bin/bash
set -e

# If a Qinling config doesn't exist we should create it and fill in with
# parameters
if [ ! -f ${CONFIG_FILE} ]; then
    oslo-config-generator \
      --config-file "${QINLING_DIR}/tools/config/config-generator.qinling.conf" \
      --output-file "${CONFIG_FILE}"

    ${INI_SET} DEFAULT debug "${LOG_DEBUG}"
    ${INI_SET} DEFAULT auth_type ${AUTH_TYPE}
    ${INI_SET} DEFAULT transport_url "${MESSAGE_BROKER_URL}"
    ${INI_SET} oslo_policy policy_file "${QINLING_DIR}/etc/qinling/policy.json"
    ${INI_SET} pecan auth_enable ${AUTH_ENABLE}
    ${INI_SET} database connection "${DATABASE_URL}"
fi

if [ ${DATABASE_URL} == "sqlite:///qinling.db" -a ! -f ./qinling.db ]
then
    qinling-db-manage --config-file "${CONFIG_FILE}" upgrade head
fi

if "${UPGRADE_DB}";
then
    qinling-db-manage --config-file "${CONFIG_FILE}" upgrade head
fi

qinling-api --config-file "${CONFIG_FILE}"
qinling-engine --config-file "${CONFIG_FILE}"
