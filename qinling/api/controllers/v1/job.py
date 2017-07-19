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

import croniter
import datetime

from dateutil import parser
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils
from pecan import rest
import six
import wsmeext.pecan as wsme_pecan

from qinling.api.controllers.v1 import resources
from qinling.api.controllers.v1 import types
from qinling.db import api as db_api
from qinling import exceptions as exc
from qinling.utils.openstack import keystone as keystone_util
from qinling.utils import rest_utils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

POST_REQUIRED = set(['function_id'])


class JobsController(rest.RestController):
    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(
        resources.Job,
        body=resources.Job,
        status_code=201
    )
    def post(self, job):
        """Creates a new job."""
        params = job.to_dict()
        if not POST_REQUIRED.issubset(set(params.keys())):
            raise exc.InputException(
                'Required param is missing. Required: %s' % POST_REQUIRED
            )

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

        LOG.info("Creating job. [job=%s]", params)

        with db_api.transaction():
            db_api.get_function(params['function_id'])

            values = {
                'name': params.get('name'),
                'pattern': pattern,
                'first_execution_time': first_time,
                'next_execution_time': next_time,
                'count': count,
                'function_id': params['function_id'],
                'function_input': params.get('function_input') or {}
            }

            if cfg.CONF.pecan.auth_enable:
                values['trust_id'] = keystone_util.create_trust().id

            try:
                db_job = db_api.create_job(values)
            except Exception:
                # Delete trust before raising exception.
                keystone_util.delete_trust(values.get('trust_id'))
                raise

        return resources.Job.from_dict(db_job.to_dict())

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(None, types.uuid, status_code=204)
    def delete(self, id):
        """Delete job."""
        LOG.info("Delete job [id=%s]" % id)

        job = db_api.get_job(id)
        trust_id = job.trust_id

        keystone_util.delete_trust(trust_id)
        db_api.delete_job(id)
