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
from swiftclient.exceptions import ClientException


def resize_image(image_path, resized_path):
    with Image.open(image_path) as image:
        image.thumbnail(tuple(x / 4 for x in image.size))
        image.save(resized_path)


def main(context, container_name, object_name):
    conn = swiftclient.Connection(
        session=context['os_session'],
        os_options={'region_name': 'RegionOne'},
    )

    # Download original image
    image_path = os.path.abspath('./%s' % object_name)
    _, obj_contents = conn.get_object(container_name, object_name)
    with open(image_path, 'w') as local:
        local.write(obj_contents)

    print('Downloaded object %s from container %s' %
          (object_name, container_name))

    thumb_path = os.path.abspath('./%s_resized.png' % object_name)
    resize_image(image_path, thumb_path)

    print('Resized.')

    # Create new container if needed
    new_container_name = '%s_resized' % container_name
    try:
        conn.head_container(new_container_name)
    except ClientException:
        conn.put_container(new_container_name)
        print("New container %s created." % new_container_name)

    # Upload resized image
    with open(thumb_path, 'r') as new_local:
        conn.put_object(
            new_container_name,
            object_name,
            contents=new_local,
            content_type='text/plain'
        )
    os.remove(image_path)
    os.remove(thumb_path)

    print('Uploaded object %s to container %s' %
          (object_name, new_container_name))
