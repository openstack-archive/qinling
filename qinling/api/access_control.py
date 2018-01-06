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

"""Access Control API server."""

from keystonemiddleware import auth_token
from oslo_config import cfg
from oslo_policy import policy

from qinling import exceptions as exc

_ENFORCER = None


def setup(app):
    if cfg.CONF.pecan.auth_enable:
        conf = dict(cfg.CONF.keystone_authtoken)

        # Change auth decisions of requests to the app itself.
        conf.update({'delay_auth_decision': True})

        _ensure_enforcer_initialization()

        return auth_token.AuthProtocol(app, conf)
    else:
        return app


def enforce(action, context, target=None, do_raise=True,
            exc=exc.NotAllowedException):
    """Verifies that the action is valid on the target in this context.

    :param action: String, representing the action to be checked.
                   This should be colon separated for clarity.
                   i.e. ``workflows:create``
    :param context: Qinling context.
    :param target: Dictionary, representing the object of the action.
                   For object creation, this should be a dictionary
                   representing the location of the object.
                   e.g. ``{'project_id': context.project_id}``
    :param do_raise: if True (the default), raises specified exception.
    :param exc: Exception to be raised if not authorized. Default is
                qinling.exceptions.NotAllowedException.

    :return: returns True if authorized and False if not authorized and
             do_raise is False.
    """
    if not cfg.CONF.pecan.auth_enable:
        return

    ctx_dict = context.to_policy_values()

    target_obj = {
        'project_id': ctx_dict['project_id'],
        'user_id': ctx_dict['user_id'],
    }

    target_obj.update(target or {})
    _ensure_enforcer_initialization()

    return _ENFORCER.enforce(
        action,
        target_obj,
        ctx_dict,
        do_raise=do_raise,
        exc=exc
    )


def _ensure_enforcer_initialization():
    global _ENFORCER
    if not _ENFORCER:
        _ENFORCER = policy.Enforcer(cfg.CONF)
        _ENFORCER.load_rules()
