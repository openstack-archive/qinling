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
