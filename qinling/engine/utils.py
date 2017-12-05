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

LOG = logging.getLogger(__name__)


def url_request(request_session, url, body=None):
    """Send request to a service url."""
    exception = None

    for a in six.moves.xrange(10):
        try:
            # Default execution duration is 3min, could be configurable
            r = request_session.post(url, json=body, timeout=(3, 180))
            return True, r.json()
        except requests.ConnectionError as e:
            exception = e
            LOG.warning("Could not connect to service. Retrying.")
            time.sleep(1)
        except Exception:
            LOG.exception("Failed to request url %s", url)
            return False, {'error': 'Function execution timeout.'}

    LOG.exception("Could not connect to function service. Reason: %s",
                  exception)

    return False, {'error': 'Internal service error.'}
