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

from oslo_db.sqlalchemy import models as oslo_models
import sqlalchemy as sa
from sqlalchemy.ext import declarative

from qinling import context
from qinling.utils import common


def id_column():
    return sa.Column(
        sa.String(36),
        primary_key=True,
        default=common.generate_unicode_uuid
    )


def get_project_id():
    return context.get_ctx().projectid


class _QinlingModelBase(oslo_models.ModelBase, oslo_models.TimestampMixin):
    """Base class for all Qinling SQLAlchemy DB Models."""

    __table__ = None

    __hash__ = object.__hash__

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False

        for col in self.__table__.columns:
            # In case of single table inheritance a class attribute
            # corresponding to a table column may not exist so we need
            # to skip these attributes.
            if (hasattr(self, col.name) and hasattr(other, col.name) and
                    getattr(self, col.name) != getattr(other, col.name)):
                return False

        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def to_dict(self):
        """sqlalchemy based automatic to_dict method."""
        d = {}

        for col in self.__table__.columns:
            d[col.name] = getattr(self, col.name)

        common.datetime_to_str(d, 'created_at')
        common.datetime_to_str(d, 'updated_at')

        return d

    def get_clone(self):
        """Clones current object, loads all fields and returns the result."""
        m = self.__class__()

        for col in self.__table__.columns:
            if hasattr(self, col.name):
                setattr(m, col.name, getattr(self, col.name))

        setattr(m, 'created_at', getattr(self, 'created_at').isoformat(' '))

        updated_at = getattr(self, 'updated_at')
        if updated_at:
            setattr(m, 'updated_at', updated_at.isoformat(' '))
        return m

    def __repr__(self):
        return '%s %s' % (type(self).__name__, self.to_dict().__repr__())


QinlingModelBase = declarative.declarative_base(cls=_QinlingModelBase)


class QinlingSecureModelBase(QinlingModelBase):
    """Base class for all secure models."""
    __abstract__ = True

    id = id_column()
    project_id = sa.Column(
        sa.String(80),
        nullable=False,
        default=get_project_id
    )
