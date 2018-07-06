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

import contextlib
import sys
import threading

from oslo_config import cfg
from oslo_db import exception as oslo_db_exc
from oslo_db.sqlalchemy import utils as db_utils
from oslo_log import log as logging
import sqlalchemy as sa

from qinling import context
from qinling.db import base as db_base
from qinling.db.sqlalchemy import filters as db_filters
from qinling.db.sqlalchemy import model_base
from qinling.db.sqlalchemy import models
from qinling import exceptions as exc
from qinling import status

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

_SCHEMA_LOCK = threading.RLock()
_initialized = False


def get_backend():
    """Consumed by openstack common code.

    The backend is this module itself.
    :return: Name of db backend.
    """
    return sys.modules[__name__]


def setup_db():
    global _initialized

    with _SCHEMA_LOCK:
        if _initialized:
            return

        try:
            models.Function.metadata.create_all(db_base.get_engine())

            _initialized = True
        except sa.exc.OperationalError as e:
            raise exc.DBError("Failed to setup database: %s" % str(e))


def drop_db():
    global _initialized

    with _SCHEMA_LOCK:
        if not _initialized:
            return

        try:
            models.Function.metadata.drop_all(db_base.get_engine())

            _initialized = False
        except Exception as e:
            raise exc.DBError("Failed to drop database: %s" % str(e))


def start_tx():
    db_base.start_tx()


def commit_tx():
    db_base.commit_tx()


def rollback_tx():
    db_base.rollback_tx()


def end_tx():
    db_base.end_tx()


@contextlib.contextmanager
def transaction():
    start_tx()

    try:
        yield
        commit_tx()
    finally:
        end_tx()


def _secure_query(model, *columns):
    query = db_base.model_query(model, columns)

    if not issubclass(model, model_base.QinlingSecureModelBase):
        return query

    if model == models.Runtime:
        query_criterion = sa.or_(
            model.project_id == context.get_ctx().projectid,
            model.is_public
        )
    else:
        query_criterion = model.project_id == context.get_ctx().projectid

    query = query.filter(query_criterion)

    return query


def _paginate_query(model, limit=None, marker=None, sort_keys=None,
                    sort_dirs=None, query=None):
    if not query:
        query = _secure_query(model)

    sort_keys = sort_keys if sort_keys else []

    if 'id' not in sort_keys:
        sort_keys.append('id')
        sort_dirs.append('asc') if sort_dirs else None

    query = db_utils.paginate_query(
        query,
        model,
        limit,
        sort_keys,
        marker=marker,
        sort_dirs=sort_dirs
    )

    return query


def _get_collection(model, insecure=False, limit=None, marker=None,
                    sort_keys=None, sort_dirs=None, fields=None, **filters):
    columns = (
        tuple([getattr(model, f) for f in fields if hasattr(model, f)])
        if fields else ()
    )

    query = (db_base.model_query(model, columns) if insecure
             else _secure_query(model, *columns))
    query = db_filters.apply_filters(query, model, **filters)
    query = _paginate_query(
        model,
        limit,
        marker,
        sort_keys,
        sort_dirs,
        query
    )

    try:
        return query.all()
    except Exception as e:
        raise exc.DBError(
            "Failed when querying database, error type: %s, "
            "error message: %s" % (e.__class__.__name__, str(e))
        )


def _get_collection_sorted_by_time(model, insecure=False, fields=None,
                                   sort_keys=['created_at'], **kwargs):
    return _get_collection(
        model=model,
        insecure=insecure,
        sort_keys=sort_keys,
        fields=fields,
        **kwargs
    )


@db_base.insecure_aware()
def _get_db_object_by_id(model, id, insecure=None):
    query = db_base.model_query(model) if insecure else _secure_query(model)

    return query.filter_by(id=id).first()


@db_base.insecure_aware()
def _delete_all(model, insecure=None, **kwargs):
    # NOTE(kong): If we use 'in_' operator in _secure_query(), delete()
    # method will raise error with default parameter. Please refer to
    # http://docs.sqlalchemy.org/en/rel_1_0/orm/query.html#sqlalchemy.orm.query.Query.delete
    query = db_base.model_query(model) if insecure else _secure_query(model)
    query.filter_by(**kwargs).delete(synchronize_session="fetch")


@db_base.insecure_aware()
def _get_db_object_by_name(model, name, insecure=None):
    query = db_base.model_query(model) if insecure else _secure_query(model)

    return query.filter_by(name=name).first()


@db_base.session_aware()
def conditional_update(model, values, expected_values, insecure=False,
                       filters=None, session=None):
    """Compare-and-swap conditional update SQLAlchemy implementation."""
    filters = filters or {}
    filters.update(expected_values)
    query = (db_base.model_query(model) if insecure else _secure_query(model))
    query = db_filters.apply_filters(query, model, **filters)
    update_args = {'synchronize_session': False}

    # Return True if we were able to change any DB entry, False otherwise
    result = query.update(values, **update_args)

    return 0 != result


@db_base.insecure_aware()
@db_base.session_aware()
def get_function(id, insecure=None, session=None):
    function = _get_db_object_by_id(models.Function, id, insecure=insecure)

    if not function:
        raise exc.DBEntityNotFoundError("Function not found [id=%s]" % id)

    return function


@db_base.session_aware()
def get_functions(session=None, **kwargs):
    return _get_collection_sorted_by_time(models.Function, **kwargs)


@db_base.session_aware()
def create_function(values, session=None):
    func = models.Function()
    func.update(values.copy())

    try:
        func.save(session=session)
    except oslo_db_exc.DBDuplicateEntry as e:
        raise exc.DBError(
            "Duplicate entry for Function: %s" % e.columns
        )

    return func


@db_base.session_aware()
def update_function(id, values, session=None):
    function = get_function(id)
    function.update(values.copy())

    return function


@db_base.session_aware()
def delete_function(id, session=None):
    function = get_function(id)

    session.delete(function)


@db_base.session_aware()
def delete_functions(session=None, **kwargs):
    return _delete_all(models.Function, **kwargs)


@db_base.session_aware()
def create_runtime(values, session=None):
    runtime = models.Runtime()
    runtime.update(values.copy())

    try:
        runtime.save(session=session)
    except oslo_db_exc.DBDuplicateEntry as e:
        raise exc.DBError(
            "Duplicate entry for Runtime: %s" % e.columns
        )

    return runtime


@db_base.session_aware()
def get_runtime(id, session=None):
    model = models.Runtime
    filters = sa.and_(
        model.id == id,
        sa.or_(model.project_id == context.get_ctx().projectid,
               model.is_public),
    )
    runtime = db_base.model_query(model).filter(filters).first()

    if not runtime:
        raise exc.DBEntityNotFoundError("Runtime not found [id=%s]" % id)

    return runtime


@db_base.session_aware()
def get_runtimes(session=None, **kwargs):
    return _get_collection_sorted_by_time(models.Runtime, **kwargs)


@db_base.session_aware()
def delete_runtime(id, session=None):
    # Because we don't allow normal user to delete runtime in api layer, so it
    # is safe to get runtime here
    runtime = get_runtime(id)
    session.delete(runtime)


@db_base.session_aware()
def update_runtime(id, values, session=None):
    # Because we don't allow normal user to update runtime in api layer, so it
    # is safe to get runtime here
    runtime = get_runtime(id)
    runtime.update(values.copy())

    return runtime


@db_base.insecure_aware()
@db_base.session_aware()
def delete_runtimes(session=None, insecure=None, **kwargs):
    return _delete_all(models.Runtime, insecure=insecure, **kwargs)


@db_base.session_aware()
def create_execution(values, session=None):
    execution = models.Execution()
    execution.update(values.copy())

    try:
        execution.save(session=session)
    except oslo_db_exc.DBDuplicateEntry as e:
        raise exc.DBError(
            "Duplicate entry for Execution: %s" % e.columns
        )

    return execution


@db_base.insecure_aware()
@db_base.session_aware()
def get_execution(id, insecure=None, session=None):
    execution = _get_db_object_by_id(models.Execution, id, insecure=insecure)

    if not execution:
        raise exc.DBEntityNotFoundError("Execution not found [id=%s]" % id)

    return execution


@db_base.session_aware()
def update_execution(id, values, session=None):
    execution = get_execution(id)
    execution.update(values.copy())

    return execution


@db_base.session_aware()
def get_executions(session=None, **kwargs):
    return _get_collection_sorted_by_time(models.Execution, **kwargs)


@db_base.session_aware()
def delete_execution(id, session=None):
    execution = get_execution(id)

    session.delete(execution)


@db_base.insecure_aware()
@db_base.session_aware()
def delete_executions(session=None, insecure=None, **kwargs):
    return _delete_all(models.Execution, insecure=insecure, **kwargs)


@db_base.session_aware()
def create_job(values, session=None):
    job = models.Job()
    job.update(values)

    try:
        job.save(session=session)
    except oslo_db_exc.DBDuplicateEntry as e:
        raise exc.DBError(
            "Duplicate entry for Job: %s" % e.columns
        )

    return job


@db_base.session_aware()
def get_job(id, session=None):
    job = _get_db_object_by_id(models.Job, id)
    if not job:
        raise exc.DBEntityNotFoundError("Job not found [id=%s]" % id)

    return job


@db_base.session_aware()
def delete_job(id, session=None):
    get_job(id)

    # Delete the job by ID and get the affected row count.
    table = models.Job.__table__
    result = session.execute(table.delete().where(table.c.id == id))

    return result.rowcount


@db_base.session_aware()
def update_job(id, values, session=None):
    job = get_job(id)
    job.update(values.copy())

    return job


@db_base.session_aware()
def get_next_jobs(before, session=None):
    return _get_collection(
        models.Job, insecure=True, sort_keys=['next_execution_time'],
        sort_dirs=['asc'], next_execution_time={'lt': before},
        status=status.RUNNING
    )


@db_base.session_aware()
def get_jobs(session=None, **kwargs):
    return _get_collection_sorted_by_time(models.Job, **kwargs)


@db_base.insecure_aware()
@db_base.session_aware()
def delete_jobs(session=None, insecure=None, **kwargs):
    return _delete_all(models.Job, insecure=insecure, **kwargs)


@db_base.session_aware()
def create_webhook(values, session=None):
    webhook = models.Webhook()
    webhook.update(values.copy())

    try:
        webhook.save(session=session)
    except oslo_db_exc.DBDuplicateEntry as e:
        raise exc.DBError(
            "Duplicate entry for webhook: %s" % e.columns
        )

    return webhook


@db_base.insecure_aware()
@db_base.session_aware()
def get_webhook(id, insecure=None, session=None):
    webhook = _get_db_object_by_id(models.Webhook, id, insecure=insecure)

    if not webhook:
        raise exc.DBEntityNotFoundError("Webhook not found [id=%s]" % id)

    return webhook


@db_base.session_aware()
def get_webhooks(session=None, **kwargs):
    return _get_collection_sorted_by_time(models.Webhook, **kwargs)


@db_base.session_aware()
def delete_webhook(id, session=None):
    webhook = get_webhook(id)
    session.delete(webhook)


@db_base.session_aware()
def update_webhook(id, values, session=None):
    webhook = get_webhook(id)
    webhook.update(values.copy())

    return webhook


@db_base.insecure_aware()
@db_base.session_aware()
def delete_webhooks(session=None, insecure=None, **kwargs):
    return _delete_all(models.Webhook, insecure=insecure, **kwargs)


@db_base.session_aware()
def increase_function_version(function_id, old_version, session=None,
                              **kwargs):
    """This function is supposed to be invoked within locking section."""
    version = models.FunctionVersion()
    kwargs.update(
        {
            "function_id": function_id,
            "version_number": old_version + 1
        }
    )
    version.update(kwargs.copy())

    try:
        version.save(session=session)
    except oslo_db_exc.DBDuplicateEntry as e:
        raise exc.DBError(
            "Duplicate entry for function_versions: %s" % e.columns
        )

    return version


@db_base.insecure_aware()
@db_base.session_aware()
def get_function_version(function_id, version, session=None, insecure=None):
    if insecure:
        query = db_base.model_query(models.FunctionVersion)
    else:
        query = _secure_query(models.FunctionVersion)

    version_db = query.filter_by(
        function_id=function_id, version_number=version
    ).first()

    if not version_db:
        raise exc.DBEntityNotFoundError(
            "FunctionVersion not found [function_id=%s, version_number=%s]" %
            (function_id, version)
        )

    return version_db


# This function is only used in unit test.
@db_base.session_aware()
def update_function_version(function_id, version, session=None, **kwargs):
    version_db = get_function_version(function_id, version, session=session)
    version_db.update(kwargs.copy())

    return version_db


@db_base.session_aware()
def delete_function_version(function_id, version, session=None):
    version_db = get_function_version(function_id, version)
    session.delete(version_db)


@db_base.session_aware()
def get_function_versions(session=None, **kwargs):
    return _get_collection_sorted_by_time(models.FunctionVersion, **kwargs)


@db_base.session_aware()
def create_function_alias(session=None, **kwargs):
    alias = models.FunctionAlias()
    alias.update(kwargs.copy())

    try:
        alias.save(session=session)
    except oslo_db_exc.DBDuplicateEntry as e:
        raise exc.DBError(
            "Duplicate entry for function_aliases: %s" % e.columns
        )

    return alias


@db_base.insecure_aware()
@db_base.session_aware()
def get_function_alias(name, session=None, insecure=None):
    alias = _get_db_object_by_name(models.FunctionAlias,
                                   name,
                                   insecure=insecure)

    if not alias:
        raise exc.DBEntityNotFoundError(
            "FunctionAlias not found [name=%s]" %
            (name)
        )

    return alias


@db_base.session_aware()
def get_function_aliases(session=None, **kwargs):
    return _get_collection_sorted_by_time(models.FunctionAlias, **kwargs)


@db_base.session_aware()
def update_function_alias(name, session=None, **kwargs):
    alias_db = get_function_alias(name, session=session)
    alias_db.update(kwargs.copy())

    return alias_db


@db_base.session_aware()
def delete_function_alias(name, session=None):
    alias_db = get_function_alias(name)
    session.delete(alias_db)


@db_base.session_aware()
def delete_function_aliases(session=None, **kwargs):
    return _delete_all(models.FunctionAlias, **kwargs)
