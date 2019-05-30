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

from keystoneauth1.identity import v3
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

    auth = v3.Token(
        auth_url=CONF.keystone_authtoken.www_authenticate_uri,
        token=ctx.auth_token,
        project_domain_name=ctx.project_domain_name,
        project_name=ctx.project_name
    )

    return session.Session(auth=auth, verify=False)


@common.disable_ssl_warnings
def get_swiftclient():
    session = _get_user_keystone_session()

    conn = swiftclient.Connection(session=session)

    return conn


@common.disable_ssl_warnings
def get_user_client():
    ctx = context.get_ctx()
    auth_url = CONF.keystone_authtoken.www_authenticate_uri
    client = ks_client.Client(
        user_id=ctx.user,
        token=ctx.auth_token,
        tenant_id=ctx.projectid,
        auth_url=auth_url
    )
    client.management_url = auth_url

    return client


@common.disable_ssl_warnings
def get_service_client():
    client = ks_client.Client(
        username=CONF.keystone_authtoken.username,
        password=CONF.keystone_authtoken.password,
        project_name=CONF.keystone_authtoken.project_name,
        auth_url=CONF.keystone_authtoken.www_authenticate_uri,
        user_domain_name=CONF.keystone_authtoken.user_domain_name,
        project_domain_name=CONF.keystone_authtoken.project_domain_name
    )
    return client


@common.disable_ssl_warnings
def get_trust_client(trust_id):
    """Get project keystone client using admin credential."""
    client = ks_client.Client(
        username=CONF.keystone_authtoken.username,
        password=CONF.keystone_authtoken.password,
        auth_url=CONF.keystone_authtoken.www_authenticate_uri,
        trust_id=trust_id
    )

    return client


@common.disable_ssl_warnings
def create_trust():
    ctx = context.get_ctx()
    user_client = get_user_client()
    trustee_id = get_service_client().user_id

    return user_client.trusts.create(
        trustor_user=ctx.user,
        trustee_user=trustee_id,
        impersonation=True,
        role_names=ctx.roles,
        project=ctx.tenant
    )


@common.disable_ssl_warnings
def delete_trust(trust_id):
    """Delete trust from keystone.

    The trust can only be deleted by original user(trustor)
    """
    if not trust_id:
        return

    try:
        client = get_user_client()
        client.trusts.delete(trust_id)
        LOG.debug('Trust %s deleted.', trust_id)
    except Exception:
        LOG.exception("Failed to delete trust [id=%s]", trust_id)


def create_trust_context(trust_id, project_id):
    """Creates Qinling context on behalf of the project."""
    if CONF.pecan.auth_enable:
        client = get_trust_client(trust_id)

        return context.Context(
            user=client.user_id,
            tenant=project_id,
            auth_token=client.auth_token,
            is_trust_scoped=True,
            trust_id=trust_id,
        )

    return context.Context(
        user=None,
        tenant=context.DEFAULT_PROJECT_ID,
        auth_token=None,
        is_admin=True
    )


def get_qinling_endpoint():
    '''Get Qinling service endpoint.'''
    if CONF.qinling_endpoint:
        return CONF.qinling_endpoint

    region = CONF.keystone_authtoken.region_name
    auth = v3.Password(
        auth_url=CONF.keystone_authtoken.www_authenticate_uri,
        username=CONF.keystone_authtoken.username,
        password=CONF.keystone_authtoken.password,
        project_name=CONF.keystone_authtoken.project_name,
        user_domain_name=CONF.keystone_authtoken.user_domain_name,
        project_domain_name=CONF.keystone_authtoken.project_domain_name,
    )
    sess = session.Session(auth=auth, verify=False)
    endpoint = sess.get_endpoint(service_type='function-engine',
                                 interface='public',
                                 region_name=region)

    return endpoint
