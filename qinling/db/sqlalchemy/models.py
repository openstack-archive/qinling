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
    __tablename__ = 'runtimes'

    name = sa.Column(sa.String(255))
    description = sa.Column(sa.String(255))
    image = sa.Column(sa.String(255), nullable=False)
    status = sa.Column(sa.String(32), nullable=False)
    is_public = sa.Column(sa.BOOLEAN, default=True)
    trusted = sa.Column(sa.BOOLEAN, default=True)


class Function(model_base.QinlingSecureModelBase):
    __tablename__ = 'functions'

    name = sa.Column(sa.String(255), nullable=True)
    description = sa.Column(sa.String(255))
    runtime_id = sa.Column(
        sa.String(36), sa.ForeignKey(Runtime.id), nullable=True
    )
    cpu = sa.Column(sa.Integer, default=0)
    memory_size = sa.Column(sa.Integer, default=0)
    timeout = sa.Column(sa.Integer)
    code = sa.Column(st.JsonLongDictType(), nullable=False)
    entry = sa.Column(sa.String(80), nullable=True)
    count = sa.Column(sa.Integer, default=0)
    trust_id = sa.Column(sa.String(80))
    latest_version = sa.Column(sa.Integer, default=0)


class Execution(model_base.QinlingSecureModelBase):
    __tablename__ = 'executions'

    function_alias = sa.Column(sa.String(255), nullable=True)
    function_id = sa.Column(sa.String(36), nullable=True)
    function_version = sa.Column(sa.Integer, default=0)
    status = sa.Column(sa.String(32), nullable=False)
    sync = sa.Column(sa.BOOLEAN, default=True)
    input = sa.Column(st.JsonLongDictType())
    result = sa.Column(st.JsonLongDictType())
    description = sa.Column(sa.String(255))
    logs = sa.Column(sa.Text(), nullable=True)


class Job(model_base.QinlingSecureModelBase):
    __tablename__ = 'jobs'

    name = sa.Column(sa.String(255), nullable=True)
    pattern = sa.Column(sa.String(32), nullable=True)
    status = sa.Column(sa.String(32), nullable=False)
    first_execution_time = sa.Column(sa.DateTime, nullable=True)
    next_execution_time = sa.Column(sa.DateTime, nullable=False)
    count = sa.Column(sa.Integer)
    function_id = sa.Column(
        sa.String(36),
        sa.ForeignKey(Function.id),
        nullable=True
    )
    function = relationship('Function', back_populates="jobs")
    function_input = sa.Column(sa.String(255), nullable=True)
    function_version = sa.Column(sa.Integer, default=0)
    function_alias = sa.Column(sa.String(255), nullable=True)

    def to_dict(self):
        d = super(Job, self).to_dict()
        common.datetime_to_str(d, 'first_execution_time')
        common.datetime_to_str(d, 'next_execution_time')
        return d


class Webhook(model_base.QinlingSecureModelBase):
    __tablename__ = 'webhooks'

    function_alias = sa.Column(sa.String(255), nullable=True)
    function_id = sa.Column(
        sa.String(36),
        sa.ForeignKey(Function.id),
        nullable=True
    )
    function_version = sa.Column(sa.Integer, nullable=True)
    description = sa.Column(sa.String(255))


class FunctionVersion(model_base.QinlingSecureModelBase):
    __tablename__ = 'function_versions'

    __table_args__ = (
        sa.UniqueConstraint('project_id', 'function_id', 'version_number'),
        sa.Index(
            '%s_project_id_function_id_version_number' % __tablename__,
            'project_id',
            'function_id',
            'version_number'
        )
    )

    function_id = sa.Column(
        sa.String(36),
        sa.ForeignKey(Function.id, ondelete='CASCADE')
    )
    function = relationship('Function', back_populates="versions")
    description = sa.Column(sa.String(255), nullable=True)
    version_number = sa.Column(sa.Integer, default=0)
    count = sa.Column(sa.Integer, default=0)


class FunctionAlias(model_base.QinlingSecureModelBase):
    __tablename__ = 'function_aliases'

    __table_args__ = (
        sa.UniqueConstraint('project_id', 'function_id', 'function_version'),
        sa.Index(
            '%s_project_id_function_id_function_version' % __tablename__,
            'project_id',
            'function_id',
            'function_version'
        ),
        sa.UniqueConstraint('project_id', 'name'),
        sa.Index(
            '%s_project_id_name' % __tablename__,
            'project_id',
            'name'
        )
    )

    function_id = sa.Column(
        sa.String(36),
        sa.ForeignKey(Function.id)
    )
    name = sa.Column(sa.String(255), nullable=False)
    description = sa.Column(sa.String(255), nullable=True)
    function_version = sa.Column(sa.Integer, default=0)


# Only get running jobs
Function.jobs = relationship(
    "Job",
    back_populates="function",
    primaryjoin=(
        "and_(Function.id==Job.function_id, "
        "~Job.status.in_(['done', 'cancelled']))"
    )
)
Function.webhooks = relationship("Webhook", uselist=True, backref="function")
Function.versions = relationship(
    "FunctionVersion",
    order_by="FunctionVersion.version_number",
    uselist=True,
    lazy='select',
    cascade="all, delete-orphan"
)
Function.aliases = relationship(
    "FunctionAlias",
    uselist=True,
    backref="function"
)
