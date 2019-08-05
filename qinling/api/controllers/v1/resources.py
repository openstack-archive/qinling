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

import json

import wsme
from wsme import types as wtypes

from qinling.api.controllers.v1 import types


class Resource(wtypes.Base):
    """REST API Resource."""

    _wsme_attributes = []

    def to_dict(self):
        d = {}

        for attr in self._wsme_attributes:
            attr_val = getattr(self, attr.name)
            if not isinstance(attr_val, wtypes.UnsetType):
                d[attr.name] = attr_val

        return d

    @classmethod
    def from_dict(cls, d):
        obj = cls()

        for key, val in d.items():
            if hasattr(obj, key):
                setattr(obj, key, val)

        return obj

    @classmethod
    def from_db_obj(cls, db_obj):
        return cls.from_dict(db_obj.to_dict())

    def __str__(self):
        """WSME based implementation of __str__."""

        res = "%s [" % type(self).__name__

        first = True
        for attr in self._wsme_attributes:
            if not first:
                res += ', '
            else:
                first = False

            res += "%s='%s'" % (attr.name, getattr(self, attr.name))

        return res + "]"

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def get_fields(cls):
        obj = cls()

        return [attr.name for attr in obj._wsme_attributes]


class ResourceList(Resource):
    """Resource containing the list of other resources."""

    next = wtypes.text
    """A link to retrieve the next subset of the resource list"""

    @property
    def collection(self):
        return getattr(self, self._type)

    @classmethod
    def convert_with_links(cls, resources, limit, url=None, fields=None,
                           **kwargs):
        resource_collection = cls()

        setattr(resource_collection, resource_collection._type, resources)

        resource_collection.next = resource_collection.get_next(
            limit,
            url=url,
            fields=fields,
            **kwargs
        )

        return resource_collection

    def has_next(self, limit):
        """Return whether resources has more items."""
        return len(self.collection) and len(self.collection) == limit

    def get_next(self, limit, url=None, fields=None, **kwargs):
        """Return a link to the next subset of the resources."""
        if not self.has_next(limit):
            return wtypes.Unset

        q_args = ''.join(
            ['%s=%s&' % (key, value) for key, value in kwargs.items()]
        )

        resource_args = (
            '?%(args)slimit=%(limit)d&marker=%(marker)s' %
            {
                'args': q_args,
                'limit': limit,
                'marker': self.collection[-1].id
            }
        )

        # Fields is handled specially here, we can move it above when it's
        # supported by all resources query.
        if fields:
            resource_args += '&fields=%s' % fields

        next_link = "%(host_url)s/v2/%(resource)s%(args)s" % {
            'host_url': url,
            'resource': self._type,
            'args': resource_args
        }

        return next_link

    def to_dict(self):
        d = {}

        for attr in self._wsme_attributes:
            attr_val = getattr(self, attr.name)

            if isinstance(attr_val, list):
                if isinstance(attr_val[0], Resource):
                    d[attr.name] = [v.to_dict() for v in attr_val]
            elif not isinstance(attr_val, wtypes.UnsetType):
                d[attr.name] = attr_val

        return d


class Link(Resource):
    """Web link."""

    href = wtypes.text
    target = wtypes.text
    rel = wtypes.text


class Function(Resource):
    id = wtypes.text
    name = wtypes.text
    description = wtypes.text
    cpu = int
    memory_size = int
    timeout = int
    runtime_id = wsme.wsattr(types.uuid, readonly=True)
    code = types.jsontype
    entry = wtypes.text
    count = wsme.wsattr(int, readonly=True)
    latest_version = wsme.wsattr(int, readonly=True)
    project_id = wsme.wsattr(wtypes.text, readonly=True)
    created_at = wtypes.text
    updated_at = wtypes.text


class Functions(ResourceList):
    functions = [Function]

    def __init__(self, **kwargs):
        self._type = 'functions'

        super(Functions, self).__init__(**kwargs)


class FunctionWorker(Resource):
    function_id = wsme.wsattr(types.uuid, readonly=True)
    function_version = wsme.wsattr(int, readonly=True)
    worker_name = wsme.wsattr(wtypes.text, readonly=True)


class FunctionWorkers(ResourceList):
    workers = [FunctionWorker]

    def __init__(self, **kwargs):
        self._type = 'workers'
        super(FunctionWorkers, self).__init__(**kwargs)


class Runtime(Resource):
    id = wtypes.text
    name = wtypes.text
    image = wtypes.text
    description = wtypes.text
    is_public = wsme.wsattr(bool, default=True)
    trusted = bool
    status = wsme.wsattr(wtypes.text, readonly=True)
    project_id = wsme.wsattr(wtypes.text, readonly=True)
    created_at = wsme.wsattr(wtypes.text, readonly=True)
    updated_at = wsme.wsattr(wtypes.text, readonly=True)


class Runtimes(ResourceList):
    runtimes = [Runtime]

    def __init__(self, **kwargs):
        self._type = 'environments'

        super(Runtimes, self).__init__(**kwargs)


class RuntimePoolCapacity(Resource):
    total = wsme.wsattr(int, readonly=True)
    available = wsme.wsattr(int, readonly=True)


class RuntimePool(Resource):
    name = wsme.wsattr(wtypes.text, readonly=True)
    capacity = wsme.wsattr(RuntimePoolCapacity, readonly=True)


class Execution(Resource):
    id = types.uuid
    function_id = wsme.wsattr(types.uuid)
    function_version = wsme.wsattr(int, default=0)
    function_alias = wsme.wsattr(wtypes.text)
    description = wtypes.text
    status = wsme.wsattr(wtypes.text, readonly=True)
    sync = bool
    input = wtypes.text
    result = wsme.wsattr(types.jsontype, readonly=True)
    project_id = wsme.wsattr(wtypes.text, readonly=True)
    created_at = wsme.wsattr(wtypes.text, readonly=True)
    updated_at = wsme.wsattr(wtypes.text, readonly=True)

    @classmethod
    def from_dict(cls, d):
        obj = cls()

        for key, val in d.items():
            if key == 'input' and val is not None:
                if val.get('__function_input'):
                    setattr(obj, key, val.get('__function_input'))
                else:
                    setattr(obj, key, json.dumps(val))
                continue
            if hasattr(obj, key):
                setattr(obj, key, val)

        return obj


class Executions(ResourceList):
    executions = [Execution]

    def __init__(self, **kwargs):
        self._type = 'executions'

        super(Executions, self).__init__(**kwargs)


class Job(Resource):
    id = types.uuid
    name = wtypes.text
    function_id = types.uuid
    function_alias = wtypes.text
    function_version = wsme.wsattr(int, default=0)
    function_input = wtypes.text
    status = wtypes.text
    pattern = wtypes.text
    count = int
    first_execution_time = wtypes.text
    next_execution_time = wtypes.text
    project_id = wsme.wsattr(wtypes.text, readonly=True)
    created_at = wsme.wsattr(wtypes.text, readonly=True)
    updated_at = wsme.wsattr(wtypes.text, readonly=True)


class Jobs(ResourceList):
    jobs = [Job]

    def __init__(self, **kwargs):
        self._type = 'jobs'

        super(Jobs, self).__init__(**kwargs)


class ScaleInfo(Resource):
    count = wtypes.IntegerType(minimum=1)


class Webhook(Resource):
    id = types.uuid
    function_id = types.uuid
    function_alias = wtypes.text
    function_version = wsme.wsattr(int)
    description = wtypes.text
    project_id = wsme.wsattr(wtypes.text, readonly=True)
    created_at = wsme.wsattr(wtypes.text, readonly=True)
    updated_at = wsme.wsattr(wtypes.text, readonly=True)
    webhook_url = wsme.wsattr(wtypes.text, readonly=True)


class Webhooks(ResourceList):
    webhooks = [Webhook]

    def __init__(self, **kwargs):
        self._type = 'webhooks'

        super(Webhooks, self).__init__(**kwargs)


class FunctionVersion(Resource):
    id = types.uuid
    description = wtypes.text
    function_id = wsme.wsattr(types.uuid, readonly=True)
    version_number = wsme.wsattr(int, readonly=True)
    count = wsme.wsattr(int, readonly=True)
    project_id = wsme.wsattr(wtypes.text, readonly=True)
    created_at = wsme.wsattr(wtypes.text, readonly=True)
    updated_at = wsme.wsattr(wtypes.text, readonly=True)


class FunctionVersions(ResourceList):
    function_versions = [FunctionVersion]

    def __init__(self, **kwargs):
        self._type = 'function_versions'

        super(FunctionVersions, self).__init__(**kwargs)


class FunctionAlias(Resource):
    id = types.uuid
    name = wtypes.text
    description = wtypes.text
    function_id = types.uuid
    function_version = wsme.wsattr(int)
    project_id = wsme.wsattr(wtypes.text, readonly=True)
    created_at = wsme.wsattr(wtypes.text, readonly=True)
    updated_at = wsme.wsattr(wtypes.text, readonly=True)


class FunctionAliases(ResourceList):
    function_aliases = [FunctionAlias]

    def __init__(self, **kwargs):
        self._type = 'function_aliases'

        super(FunctionAliases, self).__init__(**kwargs)
