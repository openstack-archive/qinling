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
from oslo_config import cfg
import swiftclient

from qinling import context

CONF = cfg.CONF


def _get_user_keystone_session():
    ctx = context.get_ctx()

    auth = generic.Token(
        auth_url=CONF.keystone_authtoken.auth_url,
        token=ctx.auth_token,
    )

    return session.Session(auth=auth, verify=False)


def get_swiftclient():
    session = _get_user_keystone_session()

    conn = swiftclient.Connection(session=session)

    return conn
