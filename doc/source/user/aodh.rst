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

How to trigger Qinling function in Aodh
=======================================

`Aodh <https://docs.openstack.org/aodh/latest/>`_ is the Alarming service
project in OpenStack that enables the ability to trigger actions based on
defined rules against metric or event data collected by
`Ceilometer <https://docs.openstack.org/ceilometer/latest/>`_ or
`Gnocchi <https://gnocchi.xyz/>`_.

We can use Aodh alarm to trigger Qinling functions by some cloud events, e.g.
when an instance is created in this guide.

Step1: Create webhook for the function in Qinling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Webhook in Qinling allows to trigger the function without providing OpenStack
credentials, the webhook URL is only known by the function owner.

Suppose we have a simple Python function that prints out a string:

.. code-block:: console

  $ cat ~/functions/hello_world.py
  def main(name='World', **kwargs):
      ret = 'Hello, %s' % name
      return ret

.. end

Create a function using the Python script:

.. code-block:: console

  $ RUNTIME_ID=bd516a15-3787-4652-938b-e25665c376e6
  $ openstack function create --runtime $RUNTIME_ID \
      --entry hello_world.main \
      --file ~/functions/hello_world.py
  +-------------+-------------------------------------------------------------------------+
  | Field       | Value                                                                   |
  +-------------+-------------------------------------------------------------------------+
  | id          | 5b25e0ea-7f8d-487a-bce6-f6a2556a1e3f                                    |
  | name        | None                                                                    |
  | description | None                                                                    |
  | count       | 0                                                                       |
  | code        | {u'source': u'package', u'md5sum': u'9bad2959cafc9d89684fe7a336de9927'} |
  | runtime_id  | bd516a15-3787-4652-938b-e25665c376e6                                    |
  | entry       | hello_world.main                                                        |
  | project_id  | 360d69d06890407eab1a44573c1f3776                                        |
  | created_at  | 2018-05-13 06:58:13.208421                                              |
  | updated_at  | None                                                                    |
  +-------------+-------------------------------------------------------------------------+

.. end

Create a webhook for the function:

.. code-block:: console

  $ function_id=5b25e0ea-7f8d-487a-bce6-f6a2556a1e3f
  $ openstack webhook create $function_id
  +-------------+-------------------------------------------------------------------------------+
  | Field       | Value                                                                         |
  +-------------+-------------------------------------------------------------------------------+
  | id          | a5f82898-a4c3-4104-ad2d-40fbafbe8857                                          |
  | function_id | 5b25e0ea-7f8d-487a-bce6-f6a2556a1e3f                                          |
  | description | None                                                                          |
  | project_id  | 360d69d06890407eab1a44573c1f3776                                              |
  | created_at  | 2018-05-13 06:59:20.616092                                                    |
  | updated_at  | None                                                                          |
  | webhook_url | http://10.0.0.14:7070/v1/webhooks/a5f82898-a4c3-4104-ad2d-40fbafbe8857/invoke |
  +-------------+-------------------------------------------------------------------------------+

.. end

The ``webhook_url`` could be used to trigger the function without any
authentication. Make note of this URL, as it will be used as the alarm action
when we create the alarm in Aodh.

Step2: Create an event alarm in Aodh
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In Aodh, we only need to define an alarm that will be triggered by the event
``compute.instance.create`` (Nova will emit the event when there is a new VM
created), using the webhook URL from Step1.

.. code-block:: console

  $ webhook_url=http://10.0.0.14:7070/v1/webhooks/a5f82898-a4c3-4104-ad2d-40fbafbe8857/invoke
  $ aodh alarm create --name qinling-alarm \
      --type event --alarm-action $webhook_url \
      --repeat-actions false --event-type compute.instance.create
  +---------------------------+------------------------------------------------------------------------------------+
  | Field                     | Value                                                                              |
  +---------------------------+------------------------------------------------------------------------------------+
  | alarm_actions             | [u'http://10.0.0.14:7070/v1/webhooks/a5f82898-a4c3-4104-ad2d-40fbafbe8857/invoke'] |
  | alarm_id                  | 1f85edea-a8a6-47ba-b1f5-9e3ac7ee61dc                                               |
  | description               | Alarm when compute.instance.create event occurred.                                 |
  | enabled                   | True                                                                               |
  | event_type                | compute.instance.create                                                            |
  | insufficient_data_actions | []                                                                                 |
  | name                      | qinling-alarm                                                                      |
  | ok_actions                | []                                                                                 |
  | project_id                | 360d69d06890407eab1a44573c1f3776                                                   |
  | query                     |                                                                                    |
  | repeat_actions            | False                                                                              |
  | severity                  | low                                                                                |
  | state                     | insufficient data                                                                  |
  | state_reason              | Not evaluated yet                                                                  |
  | state_timestamp           | 2018-05-13T07:13:03.631059                                                         |
  | time_constraints          | []                                                                                 |
  | timestamp                 | 2018-05-13T07:13:03.631059                                                         |
  | type                      | event                                                                              |
  | user_id                   | 26d9ec1da7fc4756b1940e69292565c2                                                   |
  +---------------------------+------------------------------------------------------------------------------------+

.. end

Step3: Simulate an event trigger
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For testing purpose, I wrote a Python script to generate an event for this Aodh
alarm so that we don't need to install and config Nova and Ceilometer service.
The script sends a notification with ``event_type`` as
``compute.instance.create`` to Aodh service directly. The script was tested
in a default Devstack environment.

First, create a config file for the script:

.. code-block:: console

  $ mkdir -p /etc/lingxian
  $ cat <<EOF > /etc/lingxian/lingxian.conf
  [oslo_messaging_rabbit]
  rabbit_userid = stackrabbit
  rabbit_password = password
  EOF

.. end

Download the script, modify the ``conf_file`` and ``project_id``, the
``project_id`` should be the same with the project who created the alarm. Run
the script:

.. code-block:: console

  $ curl -sSO https://raw.githubusercontent.com/lingxiankong/qinling_utils/master/aodh_notifier_simulator.py
  $ python aodh_notifier_simulator.py

.. end

Now the alarm should be triggered, and the webhook is invoked. Check the alarm
history, we could see the alarm state transition:

.. code-block:: console

  $ alarm_id=1f85edea-a8a6-47ba-b1f5-9e3ac7ee61dc
  $ aodh alarm-history show $alarm_id -f yaml
  - detail: '{"transition_reason": "Event <id=ac6ce4ae-546a-47cc-a0cb-ad1bae44ca61,event_type=compute.instance.create>
      hits the query <query=[]>.", "state": "alarm"}'
    event_id: 3250eed6-edaf-41e8-bfa6-42b060f96e75
    timestamp: '2018-05-13T08:34:47.977951'
    type: state transition
  - detail: '{"state_reason": "Not evaluated yet", "user_id": "26d9ec1da7fc4756b1940e69292565c2",
      "name": "qinling-alarm", "state": "insufficient data", "timestamp": "2018-05-13T07:13:03.631059",
      "description": "Alarm when compute.instance.create event occurred.", "enabled":
      true, "state_timestamp": "2018-05-13T07:13:03.631059", "rule": {"query": [], "event_type":
      "compute.instance.create"}, "alarm_id": "1f85edea-a8a6-47ba-b1f5-9e3ac7ee61dc",
      "time_constraints": [], "insufficient_data_actions": [], "repeat_actions": false,
      "ok_actions": [], "project_id": "360d69d06890407eab1a44573c1f3776", "type": "event",
      "alarm_actions": ["http://10.0.0.14:7070/v1/webhooks/a5f82898-a4c3-4104-ad2d-40fbafbe8857/invoke"],
      "severity": "low"}'
    event_id: 231ca53e-5d74-4191-8136-b332d2d91f1a
    timestamp: '2018-05-13T07:13:03.631059'
    type: creation

.. end

Check the function execution in Qinling:

.. code-block:: console

  $ function_id=5b25e0ea-7f8d-487a-bce6-f6a2556a1e3f
  $ openstack function execution list --filter function_id=$function_id -f yaml
  - Created_at: '2018-05-13 08:34:49'
    Description: Created by Webhook a5f82898-a4c3-4104-ad2d-40fbafbe8857
    Function_id: 5b25e0ea-7f8d-487a-bce6-f6a2556a1e3f
    Id: 41b351fa-a96b-4d86-ba77-33f7bca3dad1
    Input: '{"current": "alarm", "alarm_id": "1f85edea-a8a6-47ba-b1f5-9e3ac7ee61dc",
      "reason": "Event <id=ac6ce4ae-546a-47cc-a0cb-ad1bae44ca61,event_type=compute.instance.create>
      hits the query <query=[]>.", "severity": "low", "reason_data": {"type": "event",
      "event": {"event_type": "compute.instance.create", "traits": [["project_id", 1,
      "360d69d06890407eab1a44573c1f3776"], ["service", 1, "nova"], ["vm_name", 1, "new_instance"],
      ["vm_id", 1, "ba2b30a0-1b14-4ad4-9a66-f24ece912cad"]], "message_signature": "bcfb59e386d5375dbb7ded9910900a98536f168d377f52ae7ffd89159c0019f5",
      "raw": {}, "generated": "2017-10-03T10:02:38.305378", "message_id": "ac6ce4ae-546a-47cc-a0cb-ad1bae44ca61"}},
      "alarm_name": "qinling-alarm", "previous": "insufficient data"}'
    Project_id: 360d69d06890407eab1a44573c1f3776
    Result: '{"duration": 0.084, "output": "Hello, World"}'
    Status: success
    Sync: false
    Updated_at: '2018-05-13 08:34:53'

.. end

Conclusion
~~~~~~~~~~

Although a Qinling function can be invoked on demand, trigger the function
according to the cloud events automatically(i.e. event-driven) can bring more
power to your function and make your whole application more efficient and cost
effective.
