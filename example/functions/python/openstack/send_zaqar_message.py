import os

import requests
from zaqarclient.queues import client


def _send_message(z_client, queue_name, status, message=''):
    queue_name = queue_name or 'test_queue'
    queue = z_client.queue(queue_name)
    queue.post({"body": {'status': status, 'message': message}})
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
                if count >= 3:
                    z_client = client.Client(
                        session=context['os_session'],
                        version=2,
                    )
                    _send_message(z_client, kwargs.get('queue'), r.status_code,
                                  'Service Not Available!')
                    count = 0

                f.seek(0)
                f.write(str(count))
                f.truncate()

        print('new count: %s' % count)
    else:
        try:
            os.remove(file_name)
        except OSError:
            pass
