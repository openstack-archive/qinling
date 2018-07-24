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

"""add trusted field for runtimes table

Revision ID: 005
Revises: 004
Create Date: 2018-07-24 12:00:00.888969

"""

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(
        'runtimes',
        sa.Column('trusted', sa.BOOLEAN, nullable=False, default=True,
                  server_default="1")
    )
