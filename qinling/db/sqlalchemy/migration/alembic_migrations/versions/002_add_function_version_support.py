# Copyright 2018 OpenStack Foundation.
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

"""add function version support

Revision ID: 002
Revises: 001
Create Date: 2018-04-12 00:12:45.461970

"""

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'function_versions',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('project_id', sa.String(length=80), nullable=False),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('function_id', sa.String(length=36), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('version_number', sa.Integer, nullable=False),
        sa.Column('count', sa.Integer, nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['function_id'], [u'functions.id']),
        sa.UniqueConstraint('function_id', 'version_number', 'project_id'),
        sa.Index(
            'function_versions_project_id_function_id_version_number',
            'project_id', 'function_id', 'version_number'
        )
    )

    op.add_column(
        'functions',
        sa.Column('latest_version', sa.Integer, nullable=False),
    )

    op.add_column(
        'executions',
        sa.Column('function_version', sa.Integer, nullable=False),
    )

    op.add_column(
        'jobs',
        sa.Column('function_version', sa.Integer, nullable=False),
    )

    op.add_column(
        'webhooks',
        sa.Column('function_version', sa.Integer, nullable=False),
    )
