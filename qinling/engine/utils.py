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
import six
import tenacity

from qinling import context

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
            wait=tenacity.wait_fixed(0.5),
            stop=tenacity.stop_after_attempt(5),
            retry=tenacity.retry_if_exception_type(IOError))
        r.call(request_session.get, ping_url, timeout=(3, 3))
    except Exception as e:
        LOG.exception(
            "Failed to request url %s, error: %s", ping_url, str(e)
        )
        return False, {'error': 'Function execution failed.'}

    for a in six.moves.xrange(10):
        try:
            # Default execution max duration is 3min, could be configurable
            r = request_session.post(url, json=body, timeout=(3, 180))
            return True, r.json()
        except requests.ConnectionError as e:
            exception = e
            # NOTE(kong): Could be configurable
            time.sleep(1)
        except Exception as e:
            LOG.exception("Failed to request url %s, error: %s", url, str(e))
            return False, {'error': 'Function execution timeout.'}

    LOG.exception("Could not connect to function service. Reason: %s",
                  exception)

    return False, {'error': 'Internal service error.'}


def get_request_data(conf, function_id, execution_id, input, entry, trust_id):
    ctx = context.get_ctx()

    download_url = (
        'http://%s:%s/v1/functions/%s?download=true' %
        (conf.kubernetes.qinling_service_address,
         conf.api.port, function_id)
    )
    data = {
        'execution_id': execution_id,
        'input': input,
        'function_id': function_id,
        'entry': entry,
        'download_url': download_url,
        'request_id': ctx.request_id,
    }
    if conf.pecan.auth_enable:
        data.update(
            {
                'token': ctx.auth_token,
                'auth_url': conf.keystone_authtoken.auth_uri,
                'username': conf.keystone_authtoken.username,
                'password': conf.keystone_authtoken.password,
                'trust_id': trust_id
            }
        )

    return data
