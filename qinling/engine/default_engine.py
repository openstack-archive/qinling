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

from oslo_config import cfg
from oslo_log import log as logging

from qinling.db import api as db_api
from qinling import exceptions as exc

LOG = logging.getLogger(__name__)


class DefaultEngine(object):
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def create_runtime(self, ctx, runtime_id):
        LOG.info('Start to create runtime, id=%s', runtime_id)

        with db_api.transaction():
            runtime = db_api.get_runtime(runtime_id)
            identifier = '%s-%s' % (runtime_id, runtime.name)
            labels = {'runtime_name': runtime.name, 'runtime_id': runtime_id}

            try:
                self.orchestrator.create_pool(
                    identifier,
                    runtime.image,
                    labels=labels,
                )

                runtime.status = 'available'
            except Exception as e:
                LOG.exception(
                    'Failed to create pool for runtime %s. Error: %s',
                    runtime_id,
                    str(e)
                )

                runtime.status = 'error'

                raise exc.OrchestratorException('Failed to create pool.')

    def delete_runtime(self, ctx, runtime_id):
        LOG.info('Start to delete runtime, id=%s', runtime_id)

        with db_api.transaction():
            runtime = db_api.get_runtime(runtime_id)
            identifier = '%s-%s' % (runtime_id, runtime.name)
            labels = {'runtime_name': runtime.name, 'runtime_id': runtime_id}

            self.orchestrator.delete_pool(identifier, labels=labels)

            db_api.delete_runtime(runtime_id)

            LOG.info('Runtime %s deleted.', runtime_id)
