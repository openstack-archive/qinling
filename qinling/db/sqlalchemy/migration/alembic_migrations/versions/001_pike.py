# Copyright 2017 OpenStack Foundation.
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

"""Pike release

Revision ID: 001
Revises: None
Create Date: 2017-05-03 12:02:51.935368

"""

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None

import re

from alembic import op
import sqlalchemy as sa
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import CreateTable

from qinling.db.sqlalchemy import types as st


@compiles(CreateTable)
def _add_if_not_exists(element, compiler, **kw):
    output = compiler.visit_create_table(element, **kw)
    if element.element.info.get("check_ifexists"):
        output = re.sub(
            "^\s*CREATE TABLE", "CREATE TABLE IF NOT EXISTS", output, re.S)
    return output


def upgrade():
    op.create_table(
        'runtimes',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('project_id', sa.String(length=80), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('image', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('is_public', sa.BOOLEAN, nullable=False),
        sa.PrimaryKeyConstraint('id'),
        info={"check_ifexists": True}
    )

    op.create_table(
        'functions',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('project_id', sa.String(length=80), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('runtime_id', sa.String(length=36), nullable=True),
        sa.Column('memory_size', sa.Integer, nullable=True),
        sa.Column('timeout', sa.Integer, nullable=True),
        sa.Column('code', st.JsonLongDictType(), nullable=False),
        sa.Column('entry', sa.String(length=80), nullable=True),
        sa.Column('count', sa.Integer, nullable=False),
        sa.Column('trust_id', sa.String(length=80), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['runtime_id'], [u'runtimes.id']),
        info={"check_ifexists": True}
    )

    op.create_table(
        'executions',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('project_id', sa.String(length=80), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('function_id', sa.String(length=36), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('sync', sa.BOOLEAN, nullable=False),
        sa.Column('input', st.JsonLongDictType(), nullable=True),
        sa.Column('result', st.JsonLongDictType(), nullable=True),
        sa.Column('logs', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        info={"check_ifexists": True}
    )

    op.create_table(
        'jobs',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('project_id', sa.String(length=80), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('function_id', sa.String(length=36), nullable=False),
        sa.Column('function_input', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('pattern', sa.String(length=32), nullable=True),
        sa.Column('first_execution_time', sa.DateTime(), nullable=True),
        sa.Column('next_execution_time', sa.DateTime(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['function_id'], [u'functions.id']),
        info={"check_ifexists": True}
    )

    op.create_table(
        'webhooks',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('project_id', sa.String(length=80), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('function_id', sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        info={"check_ifexists": True}
    )
