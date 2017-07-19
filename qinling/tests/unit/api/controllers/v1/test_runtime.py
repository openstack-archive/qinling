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

import mock

from qinling.db import api as db_api
from qinling import status
from qinling.tests.unit.api import base
from qinling.tests.unit import base as test_base


class TestRuntimeController(base.APITest):
    def setUp(self):
        super(TestRuntimeController, self).setUp()

        # Insert a runtime record in db. The data will be removed in db clean
        # up.
        self.db_runtime = self.create_runtime(prefix='TestRuntimeController')
        self.runtime_id = self.db_runtime.id

    def test_get(self):
        resp = self.app.get('/v1/runtimes/%s' % self.runtime_id)

        expected = {
            'id': self.runtime_id,
            "image": self.db_runtime.image,
            "name": self.db_runtime.name,
            "project_id": test_base.DEFAULT_PROJECT_ID,
            "status": status.AVAILABLE
        }

        self.assertEqual(200, resp.status_int)
        self._assertDictContainsSubset(resp.json, expected)

    def test_get_all(self):
        resp = self.app.get('/v1/runtimes')

        expected = {
            'id': self.runtime_id,
            "image": self.db_runtime.image,
            "name": self.db_runtime.name,
            "project_id": test_base.DEFAULT_PROJECT_ID,
            "status": status.AVAILABLE
        }

        self.assertEqual(200, resp.status_int)
        actual = self._assert_single_item(
            resp.json['runtimes'], id=self.runtime_id
        )
        self._assertDictContainsSubset(actual, expected)

    @mock.patch('qinling.rpc.EngineClient.create_runtime')
    def test_post(self, mock_create_time):
        body = {
            'name': self.rand_name('runtime', prefix='TestRuntimeController'),
            'image': self.rand_name('image', prefix='TestRuntimeController'),
        }
        resp = self.app.post_json('/v1/runtimes', body)

        self.assertEqual(201, resp.status_int)
        self._assertDictContainsSubset(resp.json, body)
        mock_create_time.assert_called_once_with(resp.json['id'])

    @mock.patch('qinling.rpc.EngineClient.delete_runtime')
    def test_delete(self, mock_delete_runtime):
        resp = self.app.delete('/v1/runtimes/%s' % self.runtime_id)

        self.assertEqual(204, resp.status_int)
        mock_delete_runtime.assert_called_once_with(self.runtime_id)

    def test_delete_runtime_with_function_associated(self):
        self.create_function(self.runtime_id, prefix='TestRuntimeController')
        resp = self.app.delete(
            '/v1/runtimes/%s' % self.runtime_id, expect_errors=True
        )

        self.assertEqual(403, resp.status_int)

    def test_put_name(self):
        resp = self.app.put_json(
            '/v1/runtimes/%s' % self.runtime_id, {'name': 'new_name'}
        )

        self.assertEqual(200, resp.status_int)
        self.assertEqual('new_name', resp.json['name'])

    def test_put_image_runtime_not_available(self):
        db_runtime = db_api.create_runtime(
            {
                'name': self.rand_name(
                    'runtime', prefix='TestRuntimeController'),
                'image': self.rand_name(
                    'image', prefix='TestRuntimeController'),
                'project_id': test_base.DEFAULT_PROJECT_ID,
                'status': status.CREATING
            }
        )
        runtime_id = db_runtime.id

        resp = self.app.put_json(
            '/v1/runtimes/%s' % runtime_id, {'image': 'new_image'},
            expect_errors=True
        )

        self.assertEqual(403, resp.status_int)

    @mock.patch('qinling.rpc.EngineClient.update_runtime')
    def test_put_image(self, mock_update_runtime):
        resp = self.app.put_json(
            '/v1/runtimes/%s' % self.runtime_id, {'image': 'new_image'}
        )

        self.assertEqual(200, resp.status_int)
        self.assertEqual('new_image', resp.json['image'])
        mock_update_runtime.assert_called_once_with(
            self.runtime_id,
            image='new_image',
            pre_image=self.db_runtime.image
        )
