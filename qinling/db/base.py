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

import functools

from oslo_config import cfg
from oslo_db import options as db_options
from oslo_db.sqlalchemy import session as db_session

from qinling import context
from qinling import exceptions as exc
from qinling.utils import thread_local

# Note(dzimine): sqlite only works for basic testing.
db_options.set_defaults(cfg.CONF, connection="sqlite:///qinling.sqlite")
_FACADE = None
_DB_SESSION_THREAD_LOCAL_NAME = "db_sql_alchemy_session"


def _get_facade():
    global _FACADE
    if _FACADE is None:
        _FACADE = db_session.EngineFacade.from_config(cfg.CONF, sqlite_fk=True)
    return _FACADE


def get_session(expire_on_commit=False, autocommit=False):
    """Helper method to grab session."""
    facade = _get_facade()
    return facade.get_session(expire_on_commit=expire_on_commit,
                              autocommit=autocommit)


def get_engine():
    facade = _get_facade()
    return facade.get_engine()


def _get_thread_local_session():
    return thread_local.get_thread_local(_DB_SESSION_THREAD_LOCAL_NAME)


def _get_or_create_thread_local_session():
    ses = _get_thread_local_session()

    if ses:
        return ses, False

    ses = get_session()
    _set_thread_local_session(ses)

    return ses, True


def _set_thread_local_session(session):
    thread_local.set_thread_local(_DB_SESSION_THREAD_LOCAL_NAME, session)


def start_tx():
    """Starts transaction.

    Opens new database session and starts new transaction assuming
    there wasn't any opened sessions within the same thread.
    """
    if _get_thread_local_session():
        raise exc.DBError(
            "Database transaction has already been started."
        )

    _set_thread_local_session(get_session())


def commit_tx():
    """Commits previously started database transaction."""
    ses = _get_thread_local_session()

    if not ses:
        raise exc.DBError(
            "Nothing to commit. Database transaction"
            " has not been previously started."
        )

    ses.commit()


def rollback_tx():
    """Rolls back previously started database transaction."""
    ses = _get_thread_local_session()

    if not ses:
        raise exc.DBError(
            "Nothing to roll back. Database transaction has not been started."
        )

    ses.rollback()


def end_tx():
    """Ends transaction.

    Ends current database transaction.
    It rolls back all uncommitted changes and closes database session.
    """
    ses = _get_thread_local_session()

    if not ses:
        raise exc.DBError(
            "Database transaction has not been started."
        )

    if ses.dirty:
        rollback_tx()

    ses.close()
    _set_thread_local_session(None)


def session_aware():
    """Decorator for methods working within db session."""

    def _decorator(func):
        @functools.wraps(func)
        def _within_session(*args, **kw):
            ses, created = _get_or_create_thread_local_session()

            try:
                kw['session'] = ses

                result = func(*args, **kw)

                if created:
                    ses.commit()

                return result
            except Exception:
                if created:
                    ses.rollback()
                raise
            finally:
                if created:
                    _set_thread_local_session(None)
                    ses.close()

        return _within_session

    return _decorator


def insecure_aware():
    """Decorator for methods working within insecure db query or not."""

    def _decorator(func):
        @functools.wraps(func)
        def _with_insecure(*args, **kw):
            if kw.get('insecure') is None:
                insecure = context.get_ctx().is_admin
                kw['insecure'] = insecure
            return func(*args, **kw)

        return _with_insecure

    return _decorator


@session_aware()
def model_query(model, columns=(), session=None):
    """Query helper.

    :param model: Base model to query.
    :param columns: Optional. Which columns to be queried.
    """
    if columns:
        return session.query(*columns)

    return session.query(model)
