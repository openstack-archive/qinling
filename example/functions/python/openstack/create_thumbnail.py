from PIL import Image
import swiftclient


def main(context, container, object):
    conn = swiftclient.Connection(
        session=context['os_session'],
        os_options={'region_name': 'RegionOne'},
    )

    # obj_header = conn.head_object(container, object)
    new_container = '%s_thumb' % container

    # Download original photo
    image_path = '/%s' % object
    _, obj_contents = conn.get_object(container, object)
    with open(image_path, 'w') as local:
        local.write(obj_contents)

    print('Downloaded object % from container %s' % (object, container))

    # Resize
    SIZE = (75, 75)
    thumb_path = '/%s_thumb' % object
    im = Image.open(image_path)
    im.convert('RGB')
    im.thumbnail(SIZE, Image.ANTIALIAS)
    im.save(thumb_path, 'JPEG', quality=80)

    print('Resized.')

    # Upload thumb photo
    with open(thumb_path, 'r') as new_local:
        conn.put_object(
            new_container,
            object,
            contents=new_local,
            content_type='text/plain'
        )

    print('Uploaded object %s to container %s' % (object, new_container))

    return True
