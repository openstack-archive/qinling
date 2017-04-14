# Copyright 2017 Catalyst IT Limited
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import functools
import json

from oslo_log import log as logging
import pecan
import six
import webob
from wsme import exc as wsme_exc

from qinling import exceptions as exc

LOG = logging.getLogger(__name__)


def wrap_wsme_controller_exception(func):
    """Decorator for controllers method.

    This decorator wraps controllers method to manage wsme exceptions:
    In case of expected error it aborts the request with specific status code.
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except exc.QinlingException as e:
            pecan.response.translatable_error = e

            LOG.error('Error during API call: %s' % str(e))
            raise wsme_exc.ClientSideError(
                msg=six.text_type(e),
                status_code=e.http_code
            )

    return wrapped


def wrap_pecan_controller_exception(func):
    """Decorator for controllers method.

    This decorator wraps controllers method to manage pecan exceptions:
    In case of expected error it aborts the request with specific status code.
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except exc.QinlingException as e:
            LOG.error('Error during API call: %s' % str(e))
            return webob.Response(
                status=e.http_code,
                content_type='application/json',
                body=json.dumps(dict(faultstring=six.text_type(e))),
                charset='UTF-8'
            )

    return wrapped
