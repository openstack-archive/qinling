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

import abc

import six

STORAGE_PROVIDER_MAPPING = {}


@six.add_metaclass(abc.ABCMeta)
class PackageStorage(object):
    """PackageStorage interface."""

    @abc.abstractmethod
    def store(self, project_id, funtion, data):
        raise NotImplementedError

    @abc.abstractmethod
    def retrieve(self, project_id, function):
        raise NotImplementedError


def load_storage_providers(conf):
    global STORAGE_PROVIDER_MAPPING

    return STORAGE_PROVIDER_MAPPING
