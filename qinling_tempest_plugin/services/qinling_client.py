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

import requests
from tempest.lib import exceptions

from qinling_tempest_plugin.services import base as client_base


class QinlingClient(client_base.QinlingClientBase):
    """Tempest REST client for Qinling."""

    def delete_resource(self, res, id, ignore_notfound=False):
        try:
            resp, _ = self.delete_obj(res, id)
            return resp
        except exceptions.NotFound:
            if ignore_notfound:
                pass
            else:
                raise

    def get_resource(self, res, id):
        resp, body = self.get_obj(res, id)

        return resp, body

    def get_resources(self, res):
        resp, body = self.get_list_objs(res)

        return resp, body

    def create_runtime(self, image, name=None, is_public=True):
        req_body = {"image": image, "is_public": is_public}

        if name:
            req_body.update({'name': name})

        resp, body = self.post_json('runtimes', req_body)

        return resp, body

    def create_function(self, code, runtime_id, name='', package_data=None,
                        entry=None):
        """Create function.

        Tempest rest client doesn't support multipart upload, so use requests
        lib instead.
        """
        headers = {'X-Auth-Token': self.auth_provider.get_token()}
        req_body = {
            'name': name,
            'runtime_id': runtime_id,
            'code': json.dumps(code)
        }
        if entry:
            req_body['entry'] = entry

        req_kwargs = {
            'headers': headers,
            'data': req_body
        }
        if package_data:
            req_kwargs.update({'files': {'package': package_data}})

        url_path = '%s/v1/functions' % (self.base_url)
        resp = requests.post(url_path, **req_kwargs)

        return resp, json.loads(resp.text)

    def download_function(self, function_id):
        return self.get('/v1/functions/%s?download=true' % function_id,
                        headers={})

    def create_execution(self, function_id, input=None, sync=True):
        req_body = {'function_id': function_id, 'sync': sync, 'input': input}
        resp, body = self.post_json('executions', req_body)

        return resp, body

    def get_execution_log(self, execution_id):
        return self.get('/v1/executions/%s/log' % execution_id,
                        headers={'Accept': 'text/plain'})
