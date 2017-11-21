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

import os

import requests
from zaqarclient.queues import client


def _send_message(z_client, queue_name, status, server=''):
    queue_name = queue_name or 'test_queue'
    queue = z_client.queue(queue_name)
    queue.post({"body": {'status': status, 'server': server}})
    print 'message posted.'


def check_and_trigger(context, **kwargs):
    file_name = 'count.txt'
    r = requests.get('http://httpbin.org/status/500')

    if r.status_code != requests.codes.ok:
        if not os.path.isfile(file_name):
            count = 1
            with open(file_name, 'w') as f:
                f.write(str(count))
        else:
            with open(file_name, 'r+') as f:
                count = int(f.readline())
                count += 1
                if count == 3:
                    # Send message and stop trigger after 3 checks
                    z_client = client.Client(
                        session=context['os_session'],
                        version=2,
                    )
                    _send_message(z_client, kwargs.get('queue'), r.status_code,
                                  'api1.production.catalyst.co.nz')

                f.seek(0)
                f.write(str(count))
                f.truncate()

        print('new count: %s' % count)
    else:
        try:
            os.remove(file_name)
        except OSError:
            pass
