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
import datetime

import croniter
from dateutil import parser
from oslo_utils import timeutils
import six

from qinling.db import api as db_api
from qinling import exceptions as exc
from qinling.utils.openstack import keystone as keystone_utils


def validate_job(params):
    first_time = params.get('first_execution_time')
    pattern = params.get('pattern')
    count = params.get('count')
    start_time = timeutils.utcnow()

    if isinstance(first_time, six.string_types):
        try:
            # We need naive datetime object.
            first_time = parser.parse(first_time, ignoretz=True)
        except ValueError as e:
            raise exc.InputException(e.message)

    if not (first_time or pattern):
        raise exc.InputException(
            'Pattern or first_execution_time must be specified.'
        )

    if first_time:
        # first_time is assumed to be UTC time.
        valid_min_time = timeutils.utcnow() + datetime.timedelta(0, 60)
        if valid_min_time > first_time:
            raise exc.InputException(
                'first_execution_time must be at least 1 minute in the '
                'future.'
            )
        if not pattern and count and count > 1:
            raise exc.InputException(
                'Pattern must be provided if count is greater than 1.'
            )

        next_time = first_time
        if not (pattern or count):
            count = 1
    if pattern:
        try:
            croniter.croniter(pattern)
        except (ValueError, KeyError):
            raise exc.InputException(
                'The specified pattern is not valid: {}'.format(pattern)
            )

        if not first_time:
            next_time = croniter.croniter(pattern, start_time).get_next(
                datetime.datetime
            )

    return first_time, next_time, count


def delete_job(id, trust_id=None):
    if not trust_id:
        trust_id = db_api.get_job(id).trust_id

    modified_count = db_api.delete_job(id)
    if modified_count:
        # Delete trust only together with deleting trigger.
        keystone_utils.delete_trust(trust_id)

    return 0 != modified_count


def get_next_execution_time(pattern, start_time):
    return croniter.croniter(pattern, start_time).get_next(
        datetime.datetime
    )
