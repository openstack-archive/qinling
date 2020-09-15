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

import abc

from stevedore import driver

from qinling import exceptions as exc

ORCHESTRATOR = None


class OrchestratorBase(object, metaclass=abc.ABCMeta):
    """OrchestratorBase interface."""

    @abc.abstractmethod
    def create_pool(self, name, image, trusted=True, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def delete_pool(self, name, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def update_pool(self, name, image=None, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def get_pool(self, name, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def prepare_execution(self, function_id, function_version, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def run_execution(self, execution_id, function_id, function_version,
                      **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def delete_function(self, function_id, function_version, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def scaleup_function(self, function_id, function_version, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def delete_worker(self, worker_name, **kwargs):
        raise NotImplementedError


def load_orchestrator(conf, qinling_endpoint):
    global ORCHESTRATOR

    if not ORCHESTRATOR:
        try:
            mgr = driver.DriverManager('qinling.orchestrator',
                                       conf.engine.orchestrator,
                                       invoke_on_load=True,
                                       invoke_args=[conf, qinling_endpoint])

            ORCHESTRATOR = mgr.driver
        except Exception as e:
            raise exc.OrchestratorException(
                'Failed to load orchestrator: %s. Error: %s' %
                (conf.engine.orchestrator, str(e))
            )

    return ORCHESTRATOR
