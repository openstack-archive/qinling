import swiftclient


def stat_object(context, container, object):
    conn = swiftclient.Connection(
        session=context['os_session'],
        os_options={'region_name': 'RegionOne'},
    )

    obj_header = conn.head_object(container, object)

    return obj_header
