# -*- coding: utf-8 -*-

# Copyright 2010-2011 OpenStack Foundation
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_config import cfg
from oslotest import base

from qinling import context as auth_context
from qinling.db import api as db_api
from qinling.db import base as db_base
from qinling.db.sqlalchemy import sqlite_lock
from qinling.tests.unit import config as test_config

test_config.parse_args()
DEFAULT_PROJECT_ID = 'default'
OPT_PROJECT_ID = '55-66-77-88'


def get_context(default=True, admin=False):
    if default:
        return auth_context.Context.from_dict({
            'user_name': 'test-default-user',
            'user': '1-2-3-4',
            'tenant': DEFAULT_PROJECT_ID,
            'project_name': 'test-default-project',
            'is_admin': admin
        })
    else:
        return auth_context.Context.from_dict({
            'user_name': 'test-opt-user',
            'user': '5-6-7-8',
            'tenant': OPT_PROJECT_ID,
            'project_name': 'test-opt-project',
            'is_admin': admin
        })


class BaseTest(base.BaseTestCase):
    def override_config(self, name, override, group=None):
        """Cleanly override CONF variables."""
        cfg.CONF.set_override(name, override, group)
        self.addCleanup(cfg.CONF.clear_override, name, group)

    def _assertDictContainsSubset(self, parent, child, msg=None):
        """Checks whether child dict is a superset of parent.

        assertDictContainsSubset() in standard Python 2.7 has been deprecated
        since Python 3.2
        """
        self.assertTrue(
            set(child.items()).issubset(set(parent.items()))
        )


class DbTestCase(BaseTest):
    is_heavy_init_called = False

    def setUp(self):
        super(DbTestCase, self).setUp()

        self._heavy_init()

        self.ctx = get_context()
        auth_context.set_ctx(self.ctx)

        self.addCleanup(auth_context.set_ctx, None)
        self.addCleanup(self._clean_db)

    @classmethod
    def heavy_init(cls):
        """Runs a long initialization.

        This method runs long initialization once by class
        and can be extended by child classes.
        """
        # If using sqlite, change to memory. The default is file based.
        if cfg.CONF.database.connection.startswith('sqlite'):
            cfg.CONF.set_default('connection', 'sqlite://', group='database')

        cfg.CONF.set_default('max_overflow', -1, group='database')
        cfg.CONF.set_default('max_pool_size', 1000, group='database')

        db_api.setup_db()

    @classmethod
    def _heavy_init(cls):
        """Method that runs heavy_init().

        Make this method private to prevent extending this one.
        It runs heavy_init() only once.

        Note: setUpClass() can be used, but it magically is not invoked
        from child class in another module.
        """
        if not cls.is_heavy_init_called:
            cls.heavy_init()
            cls.is_heavy_init_called = True

    def _clean_db(self):
        db_api.delete_all()
        sqlite_lock.cleanup()

        if not cfg.CONF.database.connection.startswith('sqlite'):
            db_base.get_engine().dispose()
