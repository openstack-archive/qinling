# Copyright 2017 Catalyst IT Limited
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import time

from oslo_log import log as logging
import requests
import tenacity

from qinling import context
from qinling.db import api as db_api
from qinling import status
from qinling.utils import constants

LOG = logging.getLogger(__name__)


def url_request(request_session, url, body=None):
    """Send request to a service url."""
    exception = None

    # Send ping request first to make sure the url works
    try:
        temp = url.split('/')
        temp[-1] = 'ping'
        ping_url = '/'.join(temp)
        r = tenacity.Retrying(
            wait=tenacity.wait_fixed(1),
            stop=tenacity.stop_after_attempt(30),
            reraise=True,
            retry=tenacity.retry_if_exception_type(IOError)
        )
        r.call(request_session.get, ping_url, timeout=(3, 3), verify=False)
    except Exception as e:
        LOG.exception(
            "Failed to request url %s, error: %s", ping_url, str(e)
        )
        return False, {'output': 'Function execution failed.'}

    for a in range(10):
        res = None
        try:
            # Default execution max duration is 3min, could be configurable
            res = request_session.post(
                url, json=body, timeout=(3, 180), verify=False
            )
            return True, res.json()
        except requests.ConnectionError as e:
            exception = e
            time.sleep(1)
        except Exception as e:
            LOG.exception(
                "Failed to request url %s, error: %s", url, str(e)
            )
            if res:
                LOG.error("Response status: %s, content: %s",
                          res.status_code, res.content)

            return False, {'output': 'Function execution timeout.'}

    LOG.exception("Could not connect to function service. Reason: %s",
                  exception)

    return False, {'output': 'Internal service error.'}


def get_request_data(conf, function_id, version, execution_id, rlimit, input,
                     entry, trust_id, qinling_endpoint, timeout):
    """Prepare the request body should send to the worker."""
    ctx = context.get_ctx()

    if version == 0:
        download_url = (
            '%s/%s/functions/%s?download=true' %
            (qinling_endpoint.strip('/'), constants.CURRENT_VERSION,
             function_id)
        )
    else:
        download_url = (
            '%s/%s/functions/%s/versions/%s?download=true' %
            (qinling_endpoint.strip('/'), constants.CURRENT_VERSION,
             function_id, version)
        )

    data = {
        'execution_id': execution_id,
        'cpu': rlimit['cpu'],
        'memory_size': rlimit['memory_size'],
        'input': input,
        'function_id': function_id,
        'function_version': version,
        'entry': entry,
        'download_url': download_url,
        'request_id': ctx.request_id,
        'timeout': timeout,
    }
    if conf.pecan.auth_enable:
        data.update(
            {
                'token': ctx.auth_token,
                'auth_url': conf.keystone_authtoken.www_authenticate_uri,
                'username': conf.keystone_authtoken.username,
                'password': conf.keystone_authtoken.password,
                'trust_id': trust_id
            }
        )

    return data


def db_set_execution_status(execution_id, execution_status, logs, res):
    db_api.update_execution(
        execution_id,
        {
            'status': execution_status,
            'logs': logs,
            'result': res
        }
    )


def finish_execution(execution_id, success, res, is_image_source=False):
    logs = res.pop('logs', '')
    success = success and res.pop('success', True)

    LOG.debug(
        'Finished execution %s, success: %s', execution_id, success
    )
    db_set_execution_status(
        execution_id, status.SUCCESS if success else status.FAILED,
        logs, res
    )


def handle_execution_exception(execution_id, exc_str):
    # This method should be called from an exception handler
    LOG.exception(
        'Error running execution %s: %s', execution_id, exc_str
    )
    db_set_execution_status(
        execution_id, status.ERROR,
        '',
        {'output': 'Function execution failed.'}
    )
