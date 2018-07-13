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

from oslo_config import cfg
import oslo_messaging as messaging
from oslo_messaging.rpc import client

from qinling import context as ctx
from qinling import exceptions as exc

_TRANSPORT = None
_ENGINE_CLIENT = None


def cleanup():
    """Intended to be used by tests to recreate all RPC related objects."""

    global _TRANSPORT
    global _ENGINE_CLIENT

    _TRANSPORT = None
    _ENGINE_CLIENT = None


def get_transport():
    global _TRANSPORT

    if not _TRANSPORT:
        _TRANSPORT = messaging.get_rpc_transport(cfg.CONF)

    return _TRANSPORT


def get_engine_client():
    global _ENGINE_CLIENT

    if not _ENGINE_CLIENT:
        _ENGINE_CLIENT = EngineClient(get_transport())

    return _ENGINE_CLIENT


def _wrap_exception_and_reraise(exception):
    message = "%s: %s" % (exception.__class__.__name__, exception.args[0])

    raise exc.QinlingException(message)


def wrap_messaging_exception(method):
    """This decorator unwrap remote error in one of QinlingException.

    oslo.messaging has different behavior on raising exceptions
    when fake or rabbit transports are used. In case of rabbit
    transport it raises wrapped RemoteError which forwards directly
    to API. Wrapped RemoteError contains one of QinlingException raised
    remotely on Engine and for correct exception interpretation we
    need to unwrap and raise given exception and manually send it to
    API layer.
    """
    def decorator(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except exc.QinlingException:
            raise
        except (client.RemoteError, Exception) as e:
            if hasattr(e, 'exc_type') and hasattr(exc, e.exc_type):
                exc_cls = getattr(exc, e.exc_type)
                raise exc_cls(e.value)

            _wrap_exception_and_reraise(e)

    return decorator


class ContextSerializer(messaging.Serializer):
    def __init__(self, base):
        self._base = base

    def serialize_entity(self, context, entity):
        if not self._base:
            return entity
        return self._base.serialize_entity(context, entity)

    def deserialize_entity(self, context, entity):
        if not self._base:
            return entity
        return self._base.deserialize_entity(context, entity)

    def serialize_context(self, context):
        return context.convert_to_dict()

    def deserialize_context(self, context):
        qinling_ctx = ctx.Context.from_dict(context)
        ctx.set_ctx(qinling_ctx)

        return qinling_ctx


class EngineClient(object):
    """RPC Engine client."""

    def __init__(self, transport):
        """Constructs an RPC client for engine.

        :param transport: Messaging transport.
        """
        serializer = ContextSerializer(
            messaging.serializer.JsonPayloadSerializer())

        self.topic = cfg.CONF.engine.topic

        self._client = messaging.RPCClient(
            transport,
            messaging.Target(topic=self.topic),
            serializer=serializer
        )

    @wrap_messaging_exception
    def create_runtime(self, id):
        return self._client.prepare(topic=self.topic, server=None).cast(
            ctx.get_ctx(),
            'create_runtime',
            runtime_id=id
        )

    @wrap_messaging_exception
    def delete_runtime(self, id):
        return self._client.prepare(topic=self.topic, server=None).cast(
            ctx.get_ctx(),
            'delete_runtime',
            runtime_id=id
        )

    @wrap_messaging_exception
    def update_runtime(self, id, image=None, pre_image=None):
        return self._client.prepare(topic=self.topic, server=None).cast(
            ctx.get_ctx(),
            'update_runtime',
            runtime_id=id,
            image=image,
            pre_image=pre_image
        )

    @wrap_messaging_exception
    def get_runtime_pool(self, runtime_id):
        return self._client.prepare(topic=self.topic, server=None).call(
            ctx.get_ctx(),
            'get_runtime_pool',
            runtime_id=runtime_id
        )

    @wrap_messaging_exception
    def create_execution(self, execution_id, function_id, version, runtime_id,
                         input=None, is_sync=True):
        method_client = self._client.prepare(topic=self.topic, server=None)

        if is_sync:
            return method_client.call(
                ctx.get_ctx(),
                'create_execution',
                execution_id=execution_id,
                function_id=function_id,
                function_version=version,
                runtime_id=runtime_id,
                input=input
            )
        else:
            method_client.cast(
                ctx.get_ctx(),
                'create_execution',
                execution_id=execution_id,
                function_id=function_id,
                function_version=version,
                runtime_id=runtime_id,
                input=input
            )

    @wrap_messaging_exception
    def delete_function(self, id, version=0):
        return self._client.prepare(topic=self.topic, server=None).cast(
            ctx.get_ctx(),
            'delete_function',
            function_id=id,
            function_version=version
        )

    @wrap_messaging_exception
    def scaleup_function(self, id, runtime_id, version=0, count=1):
        return self._client.prepare(topic=self.topic, server=None).cast(
            ctx.get_ctx(),
            'scaleup_function',
            function_id=id,
            runtime_id=runtime_id,
            function_version=version,
            count=count
        )

    @wrap_messaging_exception
    def scaledown_function(self, id, version=0, count=1):
        return self._client.prepare(topic=self.topic, server=None).cast(
            ctx.get_ctx(),
            'scaledown_function',
            function_id=id,
            function_version=version,
            count=count
        )
