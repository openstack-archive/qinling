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

from qinling import exceptions as exc


def validate_next_time(next_execution_time):
    next_time = next_execution_time
    if isinstance(next_execution_time, str):
        try:
            # We need naive datetime object.
            next_time = parser.parse(next_execution_time, ignoretz=True)
        except ValueError as e:
            raise exc.InputException(str(e))

    valid_min_time = timeutils.utcnow() + datetime.timedelta(0, 60)
    if valid_min_time > next_time:
        raise exc.InputException(
            'Execution time must be at least 1 minute in the future.'
        )

    return next_time


def validate_pattern(pattern):
    try:
        croniter.croniter(pattern)
    except (ValueError, KeyError):
        raise exc.InputException(
            'The specified pattern is not valid: {}'.format(pattern)
        )


def validate_job(params):
    first_time = params.get('first_execution_time')
    pattern = params.get('pattern')
    count = params.get('count')
    start_time = timeutils.utcnow()

    if not (first_time or pattern):
        raise exc.InputException(
            'pattern or first_execution_time must be specified.'
        )

    if first_time:
        first_time = validate_next_time(first_time)
        if not pattern and count and count > 1:
            raise exc.InputException(
                'pattern must be provided if count is greater than 1.'
            )

        next_time = first_time
        if not (pattern or count):
            count = 1
    if pattern:
        validate_pattern(pattern)

        if first_time:
            start_time = first_time - datetime.timedelta(minutes=1)

        next_time = croniter.croniter(pattern, start_time).get_next(
            datetime.datetime
        )
        first_time = next_time

    return first_time, next_time, count


def get_next_execution_time(pattern, start_time):
    return croniter.croniter(pattern, start_time).get_next(
        datetime.datetime
    )
