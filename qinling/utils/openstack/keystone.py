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

from keystoneauth1.identity import generic
from keystoneauth1 import session
from keystoneclient.v3 import client as ks_client
from oslo_config import cfg
from oslo_log import log as logging
import swiftclient

from qinling import context
from qinling.utils import common

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def _get_user_keystone_session():
    ctx = context.get_ctx()

    auth = generic.Token(
        auth_url=CONF.keystone_authtoken.auth_url,
        token=ctx.auth_token,
    )

    return session.Session(auth=auth, verify=False)


@common.disable_ssl_warnings
def get_swiftclient():
    session = _get_user_keystone_session()

    conn = swiftclient.Connection(session=session)

    return conn


@common.disable_ssl_warnings
def get_keystone_client():
    session = _get_user_keystone_session()
    keystone = ks_client.Client(session=session)

    return keystone


@common.disable_ssl_warnings
def _get_admin_user_id():
    auth_url = CONF.keystone_authtoken.auth_uri
    client = ks_client.Client(
        username=CONF.keystone_authtoken.username,
        password=CONF.keystone_authtoken.password,
        project_name=CONF.keystone_authtoken.project_name,
        auth_url=auth_url,
    )

    return client.user_id


@common.disable_ssl_warnings
def create_trust():
    client = get_keystone_client()
    ctx = context.get_ctx()
    trustee_id = _get_admin_user_id()

    return client.trusts.create(
        trustor_user=ctx.user,
        trustee_user=trustee_id,
        impersonation=True,
        role_names=ctx.roles,
        project=ctx.tenant
    )


@common.disable_ssl_warnings
def delete_trust(trust_id):
    if not trust_id:
        return

    client = get_keystone_client()
    try:
        client.trusts.delete(trust_id)
    except Exception as e:
        LOG.warning("Failed to delete trust [id=%s]: %s" % (trust_id, e))
