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
import urllib

from tempest.lib.common import rest_client

urlparse = urllib.parse


class QinlingClientBase(rest_client.RestClient):
    def __init__(self, auth_provider, **kwargs):
        super(QinlingClientBase, self).__init__(auth_provider, **kwargs)

    def get_list_objs(self, obj, params=None):
        url = '/v1/%s' % obj
        query_string = ("?%s" % urlparse.urlencode(list(params.items()))
                        if params else "")
        url += query_string

        resp, body = self.get(url)
        return resp, json.loads(body)

    def delete_obj(self, obj, id):
        return self.delete('/v1/{obj}/{id}'.format(obj=obj, id=id))

    def get_obj(self, obj, id):
        resp, body = self.get('/v1/{obj}/{id}'.format(obj=obj, id=id))

        return resp, json.loads(body)

    def post_json(self, obj, req_body, extra_headers={}):
        headers = {"Content-Type": "application/json"}
        headers = dict(headers, **extra_headers)
        url_path = '/v1/%s' % obj

        resp, body = self.post(url_path, json.dumps(req_body), headers=headers)

        return resp, json.loads(body)
