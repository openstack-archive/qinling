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

Interact with other OpenStack services
======================================

It's very easy to interact with other OpenStack services in your function.
Let's take Python programming language and integration with Swift service for
an example.

At the time you create a function, you specify an entry, which is a function
in your code module that Qinling can invoke when the service executes your
code. Use the following general syntax structure when creating a function in
Python which will interact with Swift service in OpenStack.

.. code-block:: python

    import swiftclient

    def main(region_name, container, object, context=None, **kwargs):
        conn = swiftclient.Connection(
            session=context['os_session'],
            os_options={'region_name': region_name},
        )

        obj_info = conn.head_object(container, object)
        return obj_info

.. end

In the above code, note the following:

- Qinling supports most of OpenStack service clients, so you don't need to
  install ``python-swiftclient`` in your code package.
- There is a parameter named ``context``, this is a parameter provided by
  Qinling that is usually of the Python dict type. You can easily get a valid
  Keystone session object from it. As a result, you don't need to pass any
  sensitive data to Qinling in order to interact with OpenStack services.

.. note::

    Please avoid using ``context`` as your own parameter in the code.
