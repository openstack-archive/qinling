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


class QinlingException(Exception):
    """Qinling specific exception.

    Reserved for situations that are not critical for program continuation.
    It is possible to recover from this type of problems automatically and
    continue program execution. Such problems may be related with invalid user
    input (such as invalid syntax) or temporary environmental problems.

    In case if an instance of a certain exception type bubbles up to API layer
    then this type of exception it must be associated with an http code so it's
    clear how to represent it for a client.

    To correctly use this class, inherit from it and define a 'message' and
    'http_code' properties.
    """
    message = "An unknown exception occurred"
    http_code = 500

    def __init__(self, message=None):
        if message is not None:
            self.message = message

        super(QinlingException, self).__init__(
            '%d: %s' % (self.http_code, self.message))

    @property
    def code(self):
        """This is here for webob to read.

        https://github.com/Pylons/webob/blob/master/webob/exc.py
        """
        return self.http_code

    def __str__(self):
        return self.message


class InputException(QinlingException):
    http_code = 400


class UnauthorizedException(QinlingException):
    http_code = 401
    message = "Unauthorized"


class NotAllowedException(QinlingException):
    http_code = 403
    message = "Operation not allowed"


class ConflictException(QinlingException):
    http_code = 409
    message = ("The request could not be completed due to a conflict with the "
               "current state of the target resource")


class RuntimeNotAvailableException(QinlingException):
    http_code = 409
    message = "Runtime not available"


class DBError(QinlingException):
    http_code = 400


class DBEntityNotFoundError(DBError):
    http_code = 404
    message = "Object not found"


class RuntimeNotFoundException(QinlingException):
    http_code = 404
    message = "Runtime not found"


class ApplicationContextNotFoundException(QinlingException):
    http_code = 400
    message = "Application context not found"


class StorageNotFoundException(QinlingException):
    http_code = 404
    message = "Storage file not found"


class StorageProviderException(QinlingException):
    http_code = 500


class OrchestratorException(QinlingException):
    http_code = 500
    message = "Orchestrator error."


class TrustFailedException(QinlingException):
    http_code = 500
    message = "Trust operation failed."


class SwiftException(QinlingException):
    http_code = 500
    message = "Failed to communicate with Swift."


class EtcdLockException(QinlingException):
    http_code = 409
    message = 'Etcd lock failed'


class TimeoutException(QinlingException):
    http_code = 500
    message = 'Function execution timeout'
