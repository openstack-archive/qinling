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


# Function


def get_function(id):
    return IMPL.get_function(id)


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
    IMPL.delete_function(id)
