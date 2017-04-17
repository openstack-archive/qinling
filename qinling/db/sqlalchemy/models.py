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

import sqlalchemy as sa

from qinling.db.sqlalchemy import model_base
from qinling.db.sqlalchemy import types as st


class Function(model_base.QinlingSecureModelBase):
    __tablename__ = 'function'

    __table_args__ = (
        sa.UniqueConstraint('name', 'project_id'),
    )

    name = sa.Column(sa.String(255), nullable=False)
    description = sa.Column(sa.String(255))
    runtime = sa.Column(sa.String(32), nullable=False)
    memorysize = sa.Column(sa.Integer, nullable=False)
    timeout = sa.Column(sa.Integer, nullable=False)
    provider = sa.Column(sa.String(32), nullable=False)
    package = sa.Column(sa.Boolean, nullable=False)
    code = sa.Column(st.JsonLongDictType(), nullable=False)
