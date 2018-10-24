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

Create your own runtime
=======================

Although there are several reference runtime implementations in-tree, it's very
easy to develop a new runtime for the preferred programming language not
implemented so far.

.. note::

    Actually, in the production environment(especially in the public cloud),
    it's recommended that cloud providers provide their own runtime
    implementation for security reasons. Knowing how the runtime is implemented
    gives the malicious user the chance to attack the cloud environment.

Qinling uses Kubernetes as the default container orchestrator, so this guide
will describe how the runtime containers working in the Kubernetes environment.

There are two containers in a Kubernetes pod serving the runtime, one is called
"sidecar" which is responsible for downloading the function package if needed,
the other one is the actual runtime container that is also running as an HTTP
server. Once a Qinling runtime is created, there is a pool of such pods, when a
function is being executed, some pods(according to the autoscaling policy) are
chosen to run the function code.

Usually, you only need to develop the runtime container and re-use the sidecar
container in the pod. There is only one public API that the runtime container
should provide.

Public API provided by the runtime
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Request
-------

Example request:

.. code-block:: console

    POST /execute

.. end

Parameters provided by Qinling:

1.  The execution information.

    * **execution_id**: The Qinling execution UUID.
    * **download_url**: The URL sent to Qinling to download the function
      package. Here is an example for how to download function package in your
      runtime implementation using ``requests`` python library, the request is
      meant to send to the sidecar container, the final package should be put
      in ``/var/qinling/packages/<function_id>.zip`` if the request is
      successfully handled by the sidecar:

      .. code-block:: console

          resp = requests.post(
              'http://localhost:9091/download',
              json={
                  'download_url': download_url,
                  'function_id': function_id,
                  'token': params.get('token')
              }
          )

      .. end

    * **function_id**: The Qinling function UUID.
    * **entry**: The function entry that user defines when creating the
      function, e.g. "hello_world.main"
    * **input**: The dictionary of the function input that user defines when
      creating the function execution. e.g. ``{"key": "value"}``. If the user
      specifies the positional params when creating the function execution, the
      input will be something like
      ``{"__function_input": ("arg1", "arg2"), "key": "value"}``
    * **timeout**: The timeout in seconds user defines when creating the
      function, the default value is 5. Your runtime implementation should take
      this timeout value into account when executing the code. If the timeout
      is reached, you should terminate the function execution and return an
      appropriate error message.
    * **cpu**: The CPU limit user defines when creating the function. Your
      runtime is responsible for limiting the CPU resource usage when the
      function is running.
    * **memory_size**: The memory limit user defines when creating the
      function. Your runtime is responsible for limiting the memory resource
      usage when the function is running.
    * **request_id**: The request UUID for the function execution which can be
      used to track the execution for debugging purpose.

2.  The Information of the user who triggers the function execution.

    Most of that information is used for creating a Keystone session that could
    be passed to the function, so it's easy to interact with the OpenStack
    services in the function code.

    * **trust_id**: The trust UUID in Keystone. Please see for more information
      in `Keystone official doc <https://docs.openstack.org/keystone/pike/admin/identity-use-trusts.html>`__
      about Trust.
    * **auth_url**: Identity service endpoint for authorization.
    * **username**: Username for authentication.
    * **password**: Password for authentication.
    * **token**: Token for authentication.

Response
--------

Content in the response dictionary:

* **output**: The return value of the function execution if it is successful,
  otherwise the error message.
* **duration**: The execution duration in seconds.
* **logs**: The stdout content during the function execution.
* **success**: True or False. It should be False if the execution reaches
  timeout, any exception raised inside user's function or the execution is
  killed because of too much system resource consumed, etc.
