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

from oslo_config import cfg
from oslo_log import log as logging
from pecan import rest
import wsmeext.pecan as wsme_pecan

from qinling.api.controllers.v1 import resources
from qinling.api.controllers.v1 import types
from qinling.db import api as db_api
from qinling import exceptions as exc
from qinling import status
from qinling.utils import jobs
from qinling.utils.openstack import keystone as keystone_util
from qinling.utils import rest_utils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

POST_REQUIRED = set(['function_id'])


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
        LOG.info("Delete resource.", resource={'type': self.type, 'id': id})
        jobs.delete_job(id)

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
