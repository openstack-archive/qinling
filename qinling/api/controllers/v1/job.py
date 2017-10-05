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
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils
from pecan import rest
import wsmeext.pecan as wsme_pecan

from qinling.api.controllers.v1 import resources
from qinling.api.controllers.v1 import types
from qinling.db import api as db_api
from qinling import exceptions as exc
from qinling import status
from qinling.utils import jobs
from qinling.utils import rest_utils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

POST_REQUIRED = set(['function_id'])
UPDATE_ALLOWED = set(['name', 'function_input', 'status', 'pattern',
                      'next_execution_time'])


class JobsController(rest.RestController):
    type = 'job'

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

        # Check the input params.
        first_time, next_time, count = jobs.validate_job(params)
        LOG.info("Creating %s, params: %s", self.type, params)

        with db_api.transaction():
            db_api.get_function(params['function_id'])

            values = {
                'name': params.get('name'),
                'pattern': params.get('pattern'),
                'first_execution_time': first_time,
                'next_execution_time': next_time,
                'count': count,
                'function_id': params['function_id'],
                'function_input': params.get('function_input') or {},
                'status': status.RUNNING
            }
            db_job = db_api.create_job(values)

        return resources.Job.from_dict(db_job.to_dict())

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(None, types.uuid, status_code=204)
    def delete(self, id):
        LOG.info("Delete resource.", resource={'type': self.type, 'id': id})
        return db_api.delete_job(id)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Job, types.uuid)
    def get(self, id):
        LOG.info("Fetch resource.", resource={'type': self.type, 'id': id})
        job_db = db_api.get_job(id)

        return resources.Job.from_dict(job_db.to_dict())

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Jobs)
    def get_all(self):
        LOG.info("Get all %ss.", self.type)

        jobs = [resources.Job.from_dict(db_model.to_dict())
                for db_model in db_api.get_jobs()]

        return resources.Jobs(jobs=jobs)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(
        resources.Job,
        types.uuid,
        body=resources.Job
    )
    def put(self, id, job):
        """Update job definition.

        1. Can not update a finished job.
        2. Can not change job type.
        3. Allow to pause a one-shot job and resume before its first execution
           time.
        """
        values = {}
        for key in UPDATE_ALLOWED:
            if job.to_dict().get(key) is not None:
                values.update({key: job.to_dict()[key]})

        LOG.info('Update resource, params: %s', values,
                 resource={'type': self.type, 'id': id})

        new_status = values.get('status')
        pattern = values.get('pattern')
        next_execution_time = values.get('next_execution_time')

        job_db = db_api.get_job(id)

        if job_db.status in [status.DONE, status.CANCELLED]:
            raise exc.InputException('Can not update a finished job.')

        if pattern:
            if not job_db.pattern:
                raise exc.InputException('Can not change job type.')
            jobs.validate_pattern(pattern)
        elif pattern == '' and job_db.pattern:
            raise exc.InputException('Can not change job type.')

        valid_states = [status.RUNNING, status.CANCELLED, status.PAUSED]
        if new_status and new_status not in valid_states:
            raise exc.InputException('Invalid status.')

        if next_execution_time:
            values['next_execution_time'] = jobs.validate_next_time(
                next_execution_time
            )
        elif (job_db.status == status.PAUSED and
              new_status == status.RUNNING):
            p = job_db.pattern or pattern

            if not p:
                # Check if the next execution time for one-shot job is still
                # valid.
                jobs.validate_next_time(job_db.next_execution_time)
            else:
                # Update next_execution_time for recurring job.
                values['next_execution_time'] = croniter.croniter(
                    p, timeutils.utcnow()
                ).get_next(datetime.datetime)

        updated_job = db_api.update_job(id, values)
        return resources.Job.from_dict(updated_job.to_dict())
