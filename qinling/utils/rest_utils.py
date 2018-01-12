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

from qinling import context
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

            LOG.error('Error during API call: %s', six.text_type(e))
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
            LOG.error('Error during API call: %s', six.text_type(e))
            return webob.Response(
                status=e.http_code,
                content_type='application/json',
                body=json.dumps(dict(faultstring=six.text_type(e))),
                charset='UTF-8'
            )

    return wrapped


def get_filters(**params):
    """Create filters from REST request parameters.

    :param req_params: REST request parameters.
    :return: filters dictionary.
    """
    filters = {}

    for column, data in params.items():
        if data is not None:
            if isinstance(data, six.string_types):
                f_type, value = _extract_filter_type_and_value(data)

                create_or_update_filter(column, value, f_type, filters)
            else:
                create_or_update_filter(column, data, _filter=filters)

    return filters


def create_or_update_filter(column, value, filter_type='eq', _filter=None):
    """Create or Update filter.

    :param column: Column name by which user want to filter.
    :param value: Column value.
    :param filter_type: filter type. Filter type can be
                        'eq', 'neq', 'gt', 'gte', 'lte', 'in',
                        'lt', 'nin'. Default is 'eq'.
    :param _filter: Optional. If provided same filter dictionary will
                    be updated.
    :return: filter dictionary.

    """
    if _filter is None:
        _filter = {}

    _filter[column] = {filter_type: value}

    return _filter


def _extract_filter_type_and_value(data):
    """Extract filter type and its value from the data.

    :param data: REST parameter value from which filter type and
                 value can be get. It should be in format of
                 'filter_type:value'.
    :return: filter type and value.
    """
    if data.startswith("in:"):
        value = list(six.text_type(data[3:]).split(","))
        filter_type = 'in'
    elif data.startswith("nin:"):
        value = list(six.text_type(data[4:]).split(","))
        filter_type = 'nin'
    elif data.startswith("neq:"):
        value = six.text_type(data[4:])
        filter_type = 'neq'
    elif data.startswith("gt:"):
        value = six.text_type(data[3:])
        filter_type = 'gt'
    elif data.startswith("gte:"):
        value = six.text_type(data[4:])
        filter_type = 'gte'
    elif data.startswith("lt:"):
        value = six.text_type(data[3:])
        filter_type = 'lt'
    elif data.startswith("lte:"):
        value = six.text_type(data[4:])
        filter_type = 'lte'
    elif data.startswith("eq:"):
        value = six.text_type(data[3:])
        filter_type = 'eq'
    elif data.startswith("has:"):
        value = six.text_type(data[4:])
        filter_type = 'has'
    else:
        value = data
        filter_type = 'eq'

    return filter_type, value


def get_project_params(project_id, all_projects):
    ctx = context.get_ctx()

    if project_id and not ctx.is_admin:
        project_id = context.ctx().projectid
    if project_id and ctx.is_admin:
        all_projects = True

    return project_id, all_projects
