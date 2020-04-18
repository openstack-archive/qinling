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

from unittest import mock

from qinling.db import api as db_api
from qinling import status
from qinling.tests.unit.api import base
from qinling.tests.unit import base as test_base


class TestRuntimeController(base.APITest):
    def setUp(self):
        super(TestRuntimeController, self).setUp()

        # Insert a runtime record in db. The data will be removed in db clean
        # up.
        self.db_runtime = self.create_runtime()
        self.runtime_id = self.db_runtime.id

    def test_get(self):
        resp = self.app.get('/v1/runtimes/%s' % self.runtime_id)

        expected = {
            'id': self.runtime_id,
            "image": self.db_runtime.image,
            "name": self.db_runtime.name,
            "project_id": test_base.DEFAULT_PROJECT_ID,
            "status": status.AVAILABLE,
            "is_public": True,
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
            "status": status.AVAILABLE,
            "is_public": True,
        }

        self.assertEqual(200, resp.status_int)
        actual = self._assert_single_item(
            resp.json['runtimes'], id=self.runtime_id
        )
        self._assertDictContainsSubset(actual, expected)

    @mock.patch('qinling.rpc.EngineClient.create_runtime')
    def test_post(self, mock_create_time):
        body = {
            'name': self.rand_name('runtime', prefix=self.prefix),
            'image': self.rand_name('image', prefix=self.prefix),
        }
        resp = self.app.post_json('/v1/runtimes', body)

        self.assertEqual(201, resp.status_int)

        body.update({"trusted": True})
        self._assertDictContainsSubset(resp.json, body)

        mock_create_time.assert_called_once_with(resp.json['id'])

    @mock.patch('qinling.rpc.EngineClient.create_runtime')
    def test_post_without_image(self, mock_create_time):
        body = {
            'name': self.rand_name('runtime', prefix=self.prefix),
        }
        resp = self.app.post_json('/v1/runtimes', body, expect_errors=True)

        self.assertEqual(400, resp.status_int)
        mock_create_time.assert_not_called()

    @mock.patch('qinling.rpc.EngineClient.delete_runtime')
    def test_delete(self, mock_delete_runtime):
        resp = self.app.delete('/v1/runtimes/%s' % self.runtime_id)

        self.assertEqual(204, resp.status_int)
        mock_delete_runtime.assert_called_once_with(self.runtime_id)

    @mock.patch('qinling.rpc.EngineClient.delete_runtime')
    def test_delete_runtime_with_function_associated(self,
                                                     mock_delete_runtime):
        self.create_function(self.runtime_id)
        resp = self.app.delete(
            '/v1/runtimes/%s' % self.runtime_id, expect_errors=True
        )

        self.assertEqual(403, resp.status_int)
        mock_delete_runtime.assert_not_called()

    def test_put_name(self):
        resp = self.app.put_json(
            '/v1/runtimes/%s' % self.runtime_id, {'name': 'new_name'}
        )

        self.assertEqual(200, resp.status_int)
        self.assertEqual('new_name', resp.json['name'])

    def test_put_image_runtime_not_available(self):
        db_runtime = db_api.create_runtime(
            {
                'name': self.rand_name('runtime', prefix=self.prefix),
                'image': self.rand_name('image', prefix=self.prefix),
                'project_id': test_base.DEFAULT_PROJECT_ID,
                'status': status.CREATING
            }
        )
        runtime_id = db_runtime.id

        resp = self.app.put_json(
            '/v1/runtimes/%s' % runtime_id, {'image': 'new_image'},
            expect_errors=True
        )

        self.assertEqual(409, resp.status_int)

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

    @mock.patch('qinling.utils.etcd_util.get_service_url')
    @mock.patch('qinling.rpc.EngineClient.update_runtime')
    def test_put_image_not_allowed(self, mock_update_runtime, mock_etcd_url):
        mock_etcd_url.return_value = True
        function_id = self.create_function(self.runtime_id).id

        resp = self.app.put_json(
            '/v1/runtimes/%s' % self.runtime_id, {'image': 'new_image'},
            expect_errors=True
        )

        self.assertEqual(403, resp.status_int)
        mock_update_runtime.assert_not_called()
        mock_etcd_url.assert_called_once_with(function_id)

    @mock.patch('qinling.rpc.EngineClient.get_runtime_pool')
    def test_get_runtime_pool(self, mock_get_pool):
        mock_get_pool.return_value = {"total": 3, "available": 2}

        resp = self.app.get('/v1/runtimes/%s/pool' % self.runtime_id)

        expected = {
            "capacity": {
                "available": 2,
                "total": 3
            },
            "name": self.runtime_id
        }

        self.assertEqual(200, resp.status_int)
        self.assertEqual(expected, resp.json)
