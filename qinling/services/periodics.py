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

from datetime import datetime
from datetime import timedelta
import threading

from futurist import periodics
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils

from qinling import context
from qinling.db import api as db_api
from qinling.db.sqlalchemy import models
from qinling import rpc
from qinling import status
from qinling.utils import constants
from qinling.utils import etcd_util
from qinling.utils import executions
from qinling.utils import jobs
from qinling.utils.openstack import keystone as keystone_utils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF
_periodic_tasks = {}


@periodics.periodic(300)
def handle_function_service_expiration(ctx, engine):
    """Clean up resources related to expired functions.

    If it's image function, we will rely on the orchestrator itself to do the
    image clean up, e.g. image collection feature in kubernetes.
    """
    context.set_ctx(ctx)
    delta = timedelta(seconds=CONF.engine.function_service_expiration)
    expiry_time = datetime.utcnow() - delta

    results = db_api.get_functions(
        sort_keys=['updated_at'],
        insecure=True,
        updated_at={'lte': expiry_time}
    )

    for func_db in results:
        if not etcd_util.get_service_url(func_db.id, 0):
            continue

        LOG.info(
            'Deleting service mapping and workers for function '
            '%s(version 0)',
            func_db.id
        )

        # Delete resources related to the function
        engine.delete_function(ctx, func_db.id, 0)
        # Delete etcd keys
        etcd_util.delete_function(func_db.id, 0)

    versions = db_api.get_function_versions(
        sort_keys=['updated_at'],
        insecure=True,
        updated_at={'lte': expiry_time},
    )

    for v in versions:
        if not etcd_util.get_service_url(v.function_id, v.version_number):
            continue

        LOG.info(
            'Deleting service mapping and workers for function '
            '%s(version %s)',
            v.function_id, v.version_number
        )

        # Delete resources related to the function
        engine.delete_function(ctx, v.function_id, v.version_number)
        # Delete etcd keys
        etcd_util.delete_function(v.function_id, v.version_number)


@periodics.periodic(3)
def handle_job(engine_client):
    """Execute job task with no db transactions."""
    jobs_db = db_api.get_next_jobs(timeutils.utcnow() + timedelta(seconds=3))

    for job in jobs_db:
        job_id = job.id
        func_alias = job.function_alias

        if func_alias:
            alias = db_api.get_function_alias(func_alias, insecure=True)
            func_id = alias.function_id
            func_version = alias.function_version
        else:
            func_id = job.function_id
            func_version = job.function_version

        LOG.debug("Processing job: %s, function: %s(version %s)", job_id,
                  func_id, func_version)

        func_db = db_api.get_function(func_id, insecure=True)
        trust_id = func_db.trust_id

        try:
            # Setup context before schedule job.
            ctx = keystone_utils.create_trust_context(
                trust_id, job.project_id
            )
            context.set_ctx(ctx)

            if (job.count is not None and job.count > 0):
                job.count -= 1

            # Job delete/update is done using UPDATE ... FROM ... WHERE
            # non-locking clause.
            if job.count == 0:
                modified = db_api.conditional_update(
                    models.Job,
                    {
                        'status': status.DONE,
                        'count': 0
                    },
                    {
                        'id': job_id,
                        'status': status.RUNNING
                    },
                    insecure=True,
                )
            else:
                next_time = jobs.get_next_execution_time(
                    job.pattern,
                    job.next_execution_time
                )

                modified = db_api.conditional_update(
                    models.Job,
                    {
                        'next_execution_time': next_time,
                        'count': job.count
                    },
                    {
                        'id': job_id,
                        'next_execution_time': job.next_execution_time
                    },
                    insecure=True,
                )

            if not modified:
                LOG.warning(
                    'Job %s has been already handled by another periodic '
                    'task.', job_id
                )
                continue

            LOG.debug(
                "Starting to execute function %s(version %s) by job %s",
                func_id, func_version, job_id
            )

            params = {
                'function_id': func_id,
                'function_version': func_version,
                'input': job.function_input,
                'sync': False,
                'description': constants.EXECUTION_BY_JOB % job_id
            }
            executions.create_execution(engine_client, params)
        except Exception:
            LOG.exception("Failed to process job %s", job_id)
        finally:
            context.set_ctx(None)


def start_function_mapping_handler(engine):
    """Start function mapping handler thread.

    Function mapping handler is supposed to be running with engine service.
    """
    worker = periodics.PeriodicWorker([])
    worker.add(
        handle_function_service_expiration,
        ctx=context.Context(),
        engine=engine
    )
    _periodic_tasks[constants.PERIODIC_FUNC_MAPPING_HANDLER] = worker

    thread = threading.Thread(target=worker.start)
    thread.setDaemon(True)
    thread.start()

    LOG.info('Function mapping handler started.')


def start_job_handler():
    """Start job handler thread.

    Job handler is supposed to be running with api service.
    """
    worker = periodics.PeriodicWorker([])
    engine_client = rpc.get_engine_client()
    worker.add(
        handle_job,
        engine_client=engine_client
    )
    _periodic_tasks[constants.PERIODIC_JOB_HANDLER] = worker

    thread = threading.Thread(target=worker.start)
    thread.setDaemon(True)
    thread.start()

    LOG.info('Job handler started.')


def stop(task=None):
    if not task:
        for name, worker in _periodic_tasks.items():
            LOG.info('Stopping periodic task: %s', name)
            worker.stop()
            del _periodic_tasks[name]
    else:
        worker = _periodic_tasks.get(task)
        if worker:
            LOG.info('Stopping periodic task: %s', task)
            worker.stop()
            del _periodic_tasks[task]
