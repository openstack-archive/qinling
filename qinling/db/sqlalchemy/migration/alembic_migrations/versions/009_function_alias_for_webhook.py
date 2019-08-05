# Copyright 2019 - Ormuco Inc.
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

"""add function_alias field for webhooks table
Revision ID: 009
Revises: 008
"""

revision = '009'
down_revision = '008'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(
        'webhooks',
        sa.Column('function_alias', sa.String(length=255), nullable=True)
    )
