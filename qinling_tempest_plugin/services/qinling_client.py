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

from datetime import datetime
from datetime import timedelta
import json

from oslo_log import log as logging
import requests
from tempest.lib import exceptions

from qinling_tempest_plugin.services import base as client_base

LOG = logging.getLogger(__name__)


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

    def get_resources(self, res, params=None):
        resp, body = self.get_list_objs(res, params=params)

        return resp, body

    def create_runtime(self, image, name=None, is_public=True):
        req_body = {"image": image, "is_public": is_public}

        if name:
            req_body.update({'name': name})

        resp, body = self.post_json('runtimes', req_body)

        return resp, body

    def create_function(self, code, runtime_id, name='', package_data=None,
                        entry=None, timeout=None):
        """Create function.

        Tempest rest client doesn't support multipart upload, so use requests
        lib instead. As a result, we can not use self.assertRaises function for
        negative tests.
        """
        headers = {'X-Auth-Token': self.auth_provider.get_token()}
        req_body = {
            'name': name,
            'runtime_id': runtime_id,
            'code': json.dumps(code),
            'timeout': timeout
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

        LOG.info('Request: %s POST %s', resp.status_code, url_path)

        return resp, json.loads(resp.text)

    def update_function(self, function_id, package_data=None, code=None,
                        entry=None, **kwargs):
        headers = {'X-Auth-Token': self.auth_provider.get_token()}

        req_body = {}
        if code:
            req_body['code'] = json.dumps(code)
        if entry:
            req_body['entry'] = entry
        req_body.update(kwargs)

        req_kwargs = {
            'headers': headers,
            'data': req_body
        }
        if package_data:
            req_kwargs.update({'files': {'package': package_data}})

        url_path = '%s/v1/functions/%s' % (self.base_url, function_id)
        resp = requests.put(url_path, **req_kwargs)

        LOG.info('Request: %s PUT %s', resp.status_code, url_path)

        return resp, json.loads(resp.text)

    def get_function(self, function_id):
        resp, body = self.get(
            '/v1/functions/{id}'.format(id=function_id),
        )

        return resp, json.loads(body)

    def download_function(self, function_id):
        return self.get('/v1/functions/%s?download=true' % function_id,
                        headers={})

    def detach_function(self, function_id, version=0):
        if version == 0:
            url = '/v1/functions/%s/detach' % function_id
        else:
            url = '/v1/functions/%s/versions/%s/detach' % \
                  (function_id, version)

        return self.post(url, None, headers={})

    def create_execution(self, function_id=None, alias_name=None, input=None,
                         sync=True, version=0):
        """Create execution.

        alias_name takes precedence over function_id.
        """
        if alias_name:
            req_body = {
                'function_alias': alias_name,
                'sync': sync,
                'input': input
            }
        elif function_id:
            req_body = {
                'function_id': function_id,
                'function_version': version,
                'sync': sync,
                'input': input
            }
        else:
            raise Exception("Either alias_name or function_id must be "
                            "provided.")

        resp, body = self.post_json('executions', req_body)

        return resp, body

    def get_execution_log(self, execution_id):
        resp, body = self.get('/v1/executions/%s/log' % execution_id,
                              headers={'Accept': 'text/plain'})
        return resp, str(body)

    def get_function_workers(self, function_id, version=0):
        q_params = None
        if version > 0:
            q_params = "/?function_version=%s" % version

        url = 'functions/%s/workers' % function_id
        if q_params:
            url += q_params

        return self.get_resources(url)

    def create_webhook(self, function_id=None, function_alias=None,
                       version=0):
        """Create webhook.

        function_alias takes precedence over function_id.
        """
        if function_alias:
            req_body = {'function_alias': function_alias}
        elif function_id:
            req_body = {
                'function_id': function_id,
                'function_version': version
            }
        else:
            raise Exception("Either function_alias or function_id must be "
                            "provided.")
        resp, body = self.post_json('webhooks', req_body)
        return resp, body

    def create_job(self, function_id=None, function_alias=None, version=0,
                   first_execution_time=None):
        """Create job.

        function_alias takes precedence over function_id.
        """
        if function_alias:
            req_body = {'function_alias': function_alias}
        elif function_id:
            req_body = {
                'function_id': function_id,
                'function_version': version
            }
        else:
            raise Exception("Either function_alias or function_id must be "
                            "provided.")

        if not first_execution_time:
            first_execution_time = str(
                datetime.utcnow() + timedelta(hours=1)
            )
        req_body.update({'first_execution_time': first_execution_time})

        resp, body = self.post_json('jobs', req_body)
        return resp, body

    def create_function_version(self, function_id, description=None):
        req_body = {}
        if description is not None:
            req_body['description'] = description

        resp, body = self.post_json(
            'functions/%s/versions' % function_id,
            req_body
        )

        return resp, body

    def delete_function_version(self, function_id, version,
                                ignore_notfound=False):
        try:
            resp, _ = self.delete(
                '/v1/functions/{id}/versions/{version}'.format(
                    id=function_id, version=version)
            )
            return resp
        except exceptions.NotFound:
            if ignore_notfound:
                pass
            else:
                raise

    def get_function_version(self, function_id, version):
        resp, body = self.get(
            '/v1/functions/%s/versions/%s' % (function_id, version),
        )

        return resp, json.loads(body)

    def get_function_versions(self, function_id):
        resp, body = self.get(
            '/v1/functions/%s/versions' % (function_id),
        )

        return resp, json.loads(body)

    def create_function_alias(self, name, function_id,
                              function_version=0, description=None):
        req_body = {
            'function_id': function_id,
            'function_version': function_version,
            'name': name
        }
        if description is not None:
            req_body['description'] = description

        resp, body = self.post_json('/aliases', req_body)

        return resp, body

    def delete_function_alias(self, alias_name, ignore_notfound=False):
        try:
            resp, _ = self.delete('/v1/aliases/%s' % alias_name)
            return resp
        except exceptions.NotFound:
            if ignore_notfound:
                pass
            else:
                raise

    def get_function_alias(self, alias_name):
        resp, body = self.get('/v1/aliases/%s' % alias_name)

        return resp, json.loads(body)

    def update_function_alias(self, alias_name, function_id=None,
                              function_version=None, description=None):
        req_body = {}
        if function_id is not None:
            req_body['function_id'] = function_id
        if function_version is not None:
            req_body['function_version'] = function_version
        if description is not None:
            req_body['description'] = description

        resp, body = self.put_json('/v1/aliases/%s' % alias_name, req_body)

        return resp, body
