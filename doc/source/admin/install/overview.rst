..
      Copyright 2018 Catalyst IT Ltd
      All Rights Reserved.
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

Service Overview
================

The Qinling project consists of the following components:

qinling-api
  A WSGI app that authenticates and routes requests to qinling-engine after
  a preliminary handling for the request.

qinling-engine
  A standalone service whose purpose is to process operations such as runtime
  maintenance, function execution operations, function autoscaling, etc.

kubernetes
  Qinling uses kubernetes as the default backend orchestrator, in order to
  manage and maintain the underlying pods to run the functions.

database
  Qinling needs to interact with the database(usually MySQL) to store and
  retrieve resource information.

etcd
  etcd is a distributed key-value store that provides fast read/write
  operations for some specific internal resources in Qinling such as the
  mapping from functions to the function services, mapping from function to the
  workers, etc. In addition, etcd provides the locking mechanism in Qinling.

Messaging queue
  Routes information between the Qinling processes.

Additionally, users can interact with Qinling service either by sending HTTP
request or using openstack CLI provided by
`python-qinlingclient <https://docs.openstack.org/python-qinlingclient/latest/>`_.
Qinling Horizon dashboard is also available
`here <https://docs.openstack.org/qinling-dashboard/latest/>`_.
