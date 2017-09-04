# Copyright 2017 Catalyst IT Ltd
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

import json

from qinling_tempest_plugin.services import base as client_base


class QinlingClient(client_base.QinlingClientBase):
    """Tempest REST client for Qinling."""

    def create_runtime(self, image, name=None):
        body = {"image": image}

        if name:
            body.update({'name': name})

        resp, body = self.post('runtimes', json.dumps(body))
        self.runtimes.append(json.loads(body)['id'])

        return resp, json.loads(body)
