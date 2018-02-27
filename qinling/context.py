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
import re

from oslo_config import cfg
from oslo_context import context as oslo_context
import pecan
from pecan import hooks

from qinling import exceptions as exc
from qinling.utils import thread_local

CONF = cfg.CONF
ALLOWED_WITHOUT_AUTH = ['/', '/v1/']
WEBHOOK_REG = '^/v1/webhooks/[a-f0-9-]+/invoke$'
CTX_THREAD_LOCAL_NAME = "QINLING_APP_CTX_THREAD_LOCAL"
DEFAULT_PROJECT_ID = "default"


def authenticate(req):
    # Refer to:
    # https://docs.openstack.org/keystonemiddleware/latest/middlewarearchitecture.html#exchanging-user-information
    identity_status = req.headers.get('X-Identity-Status')
    service_identity_status = req.headers.get('X-Service-Identity-Status')

    if (identity_status == 'Confirmed' or
            service_identity_status == 'Confirmed'):
        return

    if req.headers.get('X-Auth-Token'):
        msg = 'Auth token is invalid: %s' % req.headers['X-Auth-Token']
    else:
        msg = 'Authentication required'

    raise exc.UnauthorizedException(msg)


class AuthHook(hooks.PecanHook):
    def before(self, state):
        if not CONF.pecan.auth_enable:
            return
        if state.request.path in ALLOWED_WITHOUT_AUTH:
            return
        if re.search(WEBHOOK_REG, state.request.path):
            return

        try:
            authenticate(state.request)
        except Exception as e:
            msg = "Failed to validate access token: %s" % str(e)

            pecan.abort(
                status_code=401,
                detail=msg,
                headers={'Server-Error-Message': msg}
            )


def has_ctx():
    return thread_local.has_thread_local(CTX_THREAD_LOCAL_NAME)


def get_ctx():
    if not has_ctx():
        raise exc.ApplicationContextNotFoundException()

    return thread_local.get_thread_local(CTX_THREAD_LOCAL_NAME)


def set_ctx(new_ctx):
    thread_local.set_thread_local(CTX_THREAD_LOCAL_NAME, new_ctx)


class Context(oslo_context.RequestContext):
    def __init__(self, is_trust_scoped=False, trust_id=None, is_admin=False,
                 **kwargs):
        self.is_trust_scoped = is_trust_scoped
        self.trust_id = trust_id

        super(Context, self).__init__(is_admin=is_admin, **kwargs)

    @property
    def projectid(self):
        if CONF.pecan.auth_enable:
            return self.project_id
        else:
            return DEFAULT_PROJECT_ID

    def convert_to_dict(self):
        """Return a dictionary of context attributes.

        Use get_logging_values() instead of to_dict() from parent class to get
        more information from the context. This method is not named "to_dict"
        to avoid recursive calling.
        """
        ctx_dict = self.get_logging_values()
        ctx_dict.update(
            {
                'is_trust_scoped': self.is_trust_scoped,
                'trust_id': self.trust_id,
                'auth_token': self.auth_token,
            }
        )

        return ctx_dict

    @classmethod
    def from_dict(cls, values, **kwargs):
        """Construct a context object from a provided dictionary."""
        kwargs.setdefault(
            'is_trust_scoped', values.get('is_trust_scoped', False)
        )
        kwargs.setdefault('trust_id', values.get('trust_id'))

        return super(Context, cls).from_dict(values, **kwargs)

    @classmethod
    def from_environ(cls, env):
        context = super(Context, cls).from_environ(env)
        context.is_admin = True if 'admin' in context.roles else False

        return context


class ContextHook(hooks.PecanHook):
    def before(self, state):
        context_obj = Context.from_environ(state.request.environ)
        set_ctx(context_obj)

    def after(self, state):
        set_ctx(None)
