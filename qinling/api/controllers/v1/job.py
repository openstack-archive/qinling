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
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from qinling.api import access_control as acl
from qinling.api.controllers.v1 import resources
from qinling.api.controllers.v1 import types
from qinling import context
from qinling.db import api as db_api
from qinling import exceptions as exc
from qinling import status
from qinling.utils import jobs
from qinling.utils import rest_utils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

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
        if not (params.get("function_id") or params.get("function_alias")):
            raise exc.InputException(
                'Either function_alias or function_id must be provided.'
            )

        LOG.info("Creating %s, params: %s", self.type, params)

        # Check the input params.
        first_time, next_time, count = jobs.validate_job(params)

        version = params.get('function_version', 0)
        function_alias = params.get('function_alias')

        if function_alias:
            # Check if the alias exists.
            db_api.get_function_alias(function_alias)
        else:
            # Check the function(version) exists.
            db_api.get_function(params['function_id'])
            if version > 0:
                # Check if the version exists.
                db_api.get_function_version(params['function_id'], version)

        values = {
            'name': params.get('name'),
            'pattern': params.get('pattern'),
            'first_execution_time': first_time,
            'next_execution_time': next_time,
            'count': count,
            'function_alias': function_alias,
            'function_id': params.get("function_id"),
            'function_version': version,
            'function_input': params.get('function_input'),
            'status': status.RUNNING
        }
        db_job = db_api.create_job(values)

        return resources.Job.from_db_obj(db_job)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(None, types.uuid, status_code=204)
    def delete(self, id):
        LOG.info("Delete resource.", resource={'type': self.type, 'id': id})
        return db_api.delete_job(id)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Job, types.uuid)
    def get(self, id):
        LOG.info("Get resource.", resource={'type': self.type, 'id': id})
        job_db = db_api.get_job(id)

        return resources.Job.from_db_obj(job_db)

    @rest_utils.wrap_wsme_controller_exception
    @wsme_pecan.wsexpose(resources.Jobs, bool, wtypes.text)
    def get_all(self, all_projects=False, project_id=None):
        project_id, all_projects = rest_utils.get_project_params(
            project_id, all_projects
        )
        if all_projects:
            acl.enforce('job:get_all:all_projects', context.get_ctx())

        filters = rest_utils.get_filters(
            project_id=project_id,
        )
        LOG.info("Get all %ss. filters=%s", self.type, filters)
        db_jobs = db_api.get_jobs(insecure=all_projects, **filters)
        jobs = [resources.Job.from_db_obj(db_model)
                for db_model in db_jobs]

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
        return resources.Job.from_db_obj(updated_job)
