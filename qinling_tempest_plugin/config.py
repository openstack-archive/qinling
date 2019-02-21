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

from oslo_config import cfg

service_option = cfg.BoolOpt(
    'qinling',
    default=True,
    help="Whether or not Qinling is expected to be available"
)


qinling_group = cfg.OptGroup(name="qinling", title="Qinling Service Options")

QinlingGroup = [
    cfg.StrOpt("region",
               default="",
               help="The region name to use. If empty, the value "
                    "of identity.region is used instead. If no such region "
                    "is found in the service catalog, the first found one is "
                    "used."),
    cfg.StrOpt("catalog_type",
               default="function-engine",
               help="Catalog type of the Qinling service."),
    cfg.StrOpt('endpoint_type',
               default='publicURL',
               choices=['public', 'admin', 'internal',
                        'publicURL', 'adminURL', 'internalURL'],
               help="The endpoint type to use for the qinling service."),
    cfg.StrOpt("python_runtime_image",
               default="openstackqinling/python3-runtime:0.0.2",
               help="The Python runtime being used in the tests."),
    cfg.StrOpt("nodejs_runtime_image",
               default="openstackqinling/nodejs-runtime:0.0.1",
               help="The NodeJS runtime being used in the tests."),
    cfg.BoolOpt("allow_external_connection",
                default=False,
                help="If the tests which need external network connection "
                     "should be running."),
]
