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
from sqlalchemy.orm import relationship

from qinling.db.sqlalchemy import model_base
from qinling.db.sqlalchemy import types as st
from qinling.utils import common


class Runtime(model_base.QinlingSecureModelBase):
    __tablename__ = 'runtime'

    __table_args__ = (
        sa.UniqueConstraint('image', 'project_id'),
    )

    name = sa.Column(sa.String(255))
    description = sa.Column(sa.String(255))
    image = sa.Column(sa.String(255), nullable=False)
    status = sa.Column(sa.String(32), nullable=False)


class Function(model_base.QinlingSecureModelBase):
    __tablename__ = 'function'

    __table_args__ = (
        sa.UniqueConstraint('name', 'project_id'),
    )

    name = sa.Column(sa.String(255), nullable=False)
    description = sa.Column(sa.String(255))
    runtime_id = sa.Column(
        sa.String(36), sa.ForeignKey(Runtime.id), nullable=True
    )
    runtime = relationship('Runtime', back_populates="functions")
    memory_size = sa.Column(sa.Integer)
    timeout = sa.Column(sa.Integer)
    code = sa.Column(st.JsonLongDictType(), nullable=False)
    entry = sa.Column(sa.String(80), nullable=False)
    count = sa.Column(sa.Integer, default=0)


class FunctionServiceMapping(model_base.QinlingModelBase):
    __tablename__ = 'function_service_mapping'

    __table_args__ = (
        sa.UniqueConstraint('function_id', 'service_url'),
    )

    id = model_base.id_column()
    function_id = sa.Column(
        sa.String(36),
        sa.ForeignKey(Function.id, ondelete='CASCADE'),
    )
    service_url = sa.Column(sa.String(255), nullable=False)


class Execution(model_base.QinlingSecureModelBase):
    __tablename__ = 'execution'

    function_id = sa.Column(sa.String(36), nullable=False)
    status = sa.Column(sa.String(32), nullable=False)
    sync = sa.Column(sa.BOOLEAN, default=True)
    input = sa.Column(st.JsonLongDictType())
    output = sa.Column(st.JsonLongDictType())
    description = sa.Column(sa.String(255))


class Job(model_base.QinlingSecureModelBase):
    __tablename__ = 'job'

    name = sa.Column(sa.String(255), nullable=True)
    pattern = sa.Column(sa.String(32), nullable=True)
    status = sa.Column(sa.String(32), nullable=False)
    first_execution_time = sa.Column(sa.DateTime, nullable=True)
    next_execution_time = sa.Column(sa.DateTime, nullable=False)
    count = sa.Column(sa.Integer)
    function_id = sa.Column(
        sa.String(36),
        sa.ForeignKey(Function.id)
    )
    function = relationship('Function', back_populates="jobs")
    function_input = sa.Column(st.JsonDictType())
    trust_id = sa.Column(sa.String(80))

    def to_dict(self):
        d = super(Job, self).to_dict()
        common.datetime_to_str(d, 'first_execution_time')
        common.datetime_to_str(d, 'next_execution_time')
        return d


# Delete service mapping automatically when deleting function.
Function.service = relationship("FunctionServiceMapping", uselist=False,
                                cascade="all, delete-orphan")
Runtime.functions = relationship("Function", back_populates="runtime")
Function.jobs = relationship("Job", back_populates="function")
