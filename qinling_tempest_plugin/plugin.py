# Copyright 2015
# All Rights Reserved.
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


import os

from tempest import config
from tempest.test_discover import plugins

from qinling_tempest_plugin import config as qinling_config


class QinlingTempestPlugin(plugins.TempestPlugin):
    def load_tests(self):
        base_path = os.path.split(os.path.dirname(
            os.path.abspath(__file__))
        )[0]
        test_dir = "qinling_tempest_plugin/tests"
        full_test_dir = os.path.join(base_path, test_dir)
        return full_test_dir, base_path

    def register_opts(self, conf):
        conf.register_opt(
            qinling_config.service_option, group='service_available'
        )

        conf.register_group(qinling_config.qinling_group)
        conf.register_opts(qinling_config.QinlingGroup, group='qinling')

    def get_opt_lists(self):
        return [
            ('service_available', [qinling_config.service_option]),
            (qinling_config.qinling_group.name, qinling_config.QinlingGroup)
        ]

    def get_service_clients(self):
        qinling_config = config.service_client_config('qinling')
        params = {
            'name': 'qinling',
            'service_version': 'qinling',
            'module_path': 'qinling_tempest_plugin.services.qinling_client',
            'client_names': ['QinlingClient'],
        }
        params.update(qinling_config)
        return [params]
