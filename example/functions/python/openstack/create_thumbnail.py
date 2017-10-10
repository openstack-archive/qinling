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

from PIL import Image
import swiftclient


def resize_image(image_path, resized_path):
    with Image.open(image_path) as image:
        image.thumbnail((75, 75))
        image.save(resized_path)


def main(context, container, object):
    conn = swiftclient.Connection(
        session=context['os_session'],
        os_options={'region_name': 'RegionOne'},
    )

    new_container = '%s_thumb' % container

    # Download original photo
    image_path = '/%s' % object
    _, obj_contents = conn.get_object(container, object)
    with open(image_path, 'w') as local:
        local.write(obj_contents)

    print('Downloaded object %s from container %s' % (object, container))

    thumb_path = '/thumb_%s' % object
    resize_image(image_path, thumb_path)

    print('Resized.')

    # Upload thumb photo
    with open(thumb_path, 'r') as new_local:
        conn.put_object(
            new_container,
            object,
            contents=new_local,
            content_type='text/plain'
        )

    os.remove(image_path)
    os.remove(thumb_path)

    print('Uploaded object %s to container %s' % (object, new_container))
