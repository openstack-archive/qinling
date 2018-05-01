..
      Copyright 2017 Catalyst IT Ltd
      All Rights Reserved.
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

Qinling Features
================

This section does not intend to give you an exhaustive feature list of Qinling,
but some features which make Qinling userful, powerful, scalable and highly
available.

Auto Scaling
~~~~~~~~~~~~

With Qinling, the function invocation can be automatically scaled up and down
to meet the needs of your function. It's not necessary to monitor usage by
yourself, Qinling can scale up new workers if traffic ticks up, and scale
back down when it drops.

To handle any burst in traffic, Qinling will immediately increase the workers
concurrently executing functions by a predetermined amount. After the increased
load is handled successfully, the workers will be released in a predefined
expiration time.

Webhook
~~~~~~~

Webhooks are a low-effort way to invoke the functions in Qinling. They do
not require a bot user or authentication to use.

Sync/Async Function Executions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Qinling allows the functions to be executed either synchronously or
asynchronously. For synchronous functions, the caller will be blocked to wait
for the responses. Asynchronous functions will be executed at the same time
point and the responses will be returned to the caller immediately, the caller
could check the result later on.