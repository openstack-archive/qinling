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

from oslo_db import api as db_api


_BACKEND_MAPPING = {
    'sqlalchemy': 'qinling.db.sqlalchemy.api',
}

IMPL = db_api.DBAPI('sqlalchemy', backend_mapping=_BACKEND_MAPPING)


def setup_db():
    IMPL.setup_db()


def drop_db():
    IMPL.drop_db()


def start_tx():
    IMPL.start_tx()


def commit_tx():
    IMPL.commit_tx()


def rollback_tx():
    IMPL.rollback_tx()


def end_tx():
    IMPL.end_tx()


@contextlib.contextmanager
def transaction():
    with IMPL.transaction():
        yield


def delete_all():
    """A helper function for testing."""
    delete_jobs(insecure=True)
    delete_webhooks(insecure=True)
    delete_executions(insecure=True)
    delete_function_aliases(insecure=True)
    delete_functions(insecure=True)
    delete_runtimes(insecure=True)


def conditional_update(model, values, expected_values, **kwargs):
    return IMPL.conditional_update(model, values, expected_values, **kwargs)


def get_function(id, insecure=None):
    """Get function from db.

    'insecure' param is needed for job handler and webhook.
    """
    return IMPL.get_function(id, insecure=insecure)


def get_functions(limit=None, marker=None, sort_keys=None,
                  sort_dirs=None, fields=None, **kwargs):
    return IMPL.get_functions(
        limit=limit,
        marker=marker,
        sort_keys=sort_keys,
        sort_dirs=sort_dirs,
        fields=fields,
        **kwargs
    )


def create_function(values):
    return IMPL.create_function(values)


def update_function(id, values):
    return IMPL.update_function(id, values)


def delete_function(id):
    return IMPL.delete_function(id)


def delete_functions(**kwargs):
    return IMPL.delete_functions(**kwargs)


def create_runtime(values):
    return IMPL.create_runtime(values)


def get_runtime(id):
    return IMPL.get_runtime(id)


def get_runtimes():
    return IMPL.get_runtimes()


def delete_runtime(id):
    return IMPL.delete_runtime(id)


def update_runtime(id, values):
    return IMPL.update_runtime(id, values)


def delete_runtimes(**kwargs):
    return IMPL.delete_runtimes(**kwargs)


def create_execution(values):
    return IMPL.create_execution(values)


def get_execution(id):
    return IMPL.get_execution(id)


def get_executions(**filters):
    return IMPL.get_executions(**filters)


def delete_execution(id):
    return IMPL.delete_execution(id)


def update_execution(id, values):
    return IMPL.update_execution(id, values)


def delete_executions(**kwargs):
    return IMPL.delete_executions(**kwargs)


def create_job(values):
    return IMPL.create_job(values)


def get_job(id):
    return IMPL.get_job(id)


def get_next_jobs(before):
    return IMPL.get_next_jobs(before)


def delete_job(id):
    return IMPL.delete_job(id)


def update_job(id, values):
    return IMPL.update_job(id, values)


def get_jobs(**kwargs):
    return IMPL.get_jobs(**kwargs)


def delete_jobs(**kwargs):
    return IMPL.delete_jobs(**kwargs)


def create_webhook(values):
    return IMPL.create_webhook(values)


def get_webhook(id, insecure=None):
    return IMPL.get_webhook(id, insecure=insecure)


def get_webhooks(**kwargs):
    return IMPL.get_webhooks(**kwargs)


def delete_webhook(id):
    return IMPL.delete_webhook(id)


def update_webhook(id, values):
    return IMPL.update_webhook(id, values)


def delete_webhooks(**kwargs):
    return IMPL.delete_webhooks(**kwargs)


def increase_function_version(function_id, old_version, **kwargs):
    """This function is meant to be invoked within locking section."""
    return IMPL.increase_function_version(function_id, old_version, **kwargs)


def get_function_version(function_id, version, **kwargs):
    return IMPL.get_function_version(function_id, version, **kwargs)


# This function is only used in unit test.
def update_function_version(function_id, version, **kwargs):
    return IMPL.update_function_version(function_id, version, **kwargs)


def delete_function_version(function_id, version):
    return IMPL.delete_function_version(function_id, version)


def get_function_versions(**kwargs):
    return IMPL.get_function_versions(**kwargs)


def create_function_alias(**kwargs):
    return IMPL.create_function_alias(**kwargs)


def get_function_alias(name, **kwargs):
    return IMPL.get_function_alias(name, **kwargs)


def get_function_aliases(**kwargs):
    return IMPL.get_function_aliases(**kwargs)


def update_function_alias(name, **kwargs):
    return IMPL.update_function_alias(name, **kwargs)


def delete_function_alias(name, **kwargs):
    return IMPL.delete_function_alias(name, **kwargs)


# For unit test
def delete_function_aliases(**kwargs):
    return IMPL.delete_function_aliases(**kwargs)
