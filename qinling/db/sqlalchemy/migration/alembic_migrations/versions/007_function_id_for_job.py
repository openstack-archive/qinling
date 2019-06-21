# Copyright 2019 Catalyst Cloud Ltd.
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

"""Make function id nullable for jobs table

Revision ID: 007
Revises: 006
"""

revision = '007'
down_revision = '006'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column(
        'jobs',
        'function_id',
        existing_type=sa.String(length=36),
        nullable=True
    )
