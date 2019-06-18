.. -*- rst -*-
  
===========
 Executions
===========

Lists, creates, shows details for, and deletes function executions.

An execution runs the function and stores the return of the function.
The execution gets the returns and the prints.


Create an execution
====================

.. rest_method:: POST /v1/executions

Create an execution.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403

Request
-------

.. rest_parameters:: parameters.yaml

   - x-auth-token: x-auth-token
   - function_id: execution_function_id
   - function_alias: execution_function_alias
   - input: execution_input
   - description: execution_description
   - function_version: execution_function_version
   - sync: execution_sync

Request Example
---------------

.. literalinclude:: samples/executions/create-execution-request.json
   :language: javascript

.. literalinclude:: samples/executions/create-execution-alias-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - function_id: execution_function_id
   - input: execution_input
   - description: execution_description
   - function_version: execution_function_version
   - sync: execution_sync
   - project_id: project_id
   - status: status
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/executions/create-execution-response.json
   :language: javascript


List executions
===============

.. rest_method:: GET /v1/executions

List executions.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403

Request
-------

.. rest_parameters:: parameters.yaml

   - x-auth-token: x-auth-token

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - function_id: execution_function_id
   - input: execution_input
   - description: execution_description
   - function_version: execution_function_version
   - sync: execution_sync
   - project_id: project_id
   - status: status
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/executions/list-executions-response.json
   :language: javascript


List executions by filters
==========================

.. rest_method:: GET /v1/executions?{filter}={function_id}

List executions by filters..

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403

Request
-------

.. rest_parameters:: parameters.yaml

   - x-auth-token: x-auth-token
   - filter: path_execution_filter
   - function_id: path_function_id

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - function_id: execution_function_id
   - input: execution_input
   - description: execution_description
   - function_version: execution_function_version
   - sync: execution_sync
   - project_id: project_id
   - status: status
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/executions/list-executions-filters-response.json
   :language: javascript


Show an execution
=================

.. rest_method:: GET /v1/executions/{execution_id}

Show an execution.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403

Request
-------

.. rest_parameters:: parameters.yaml

   - x-auth-token: x-auth-token
   - execution_id: path_execution_id

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - function_id: execution_function_id
   - input: execution_input
   - description: execution_description
   - function_version: execution_function_version
   - sync: execution_sync
   - project_id: project_id
   - status: status
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/executions/show-execution-response.json
   :language: javascript


Show an execution log
=====================

.. rest_method:: GET /v1/executions/{execution_id}/log

Show an execution log.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403

Request
-------

.. rest_parameters:: parameters.yaml

   - x-auth-token: x-auth-token
   - execution_id: path_execution_id

Response Parameters
-------------------

None

Response Example
----------------

.. literalinclude:: samples/executions/show-execution-log-response.json
   :language: javascript


Delete an execution
===================

.. rest_method:: DELETE /v1/executions/{execution_id}

Delete an execution.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 204

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403

Request
-------

.. rest_parameters:: parameters.yaml

   - x-auth-token: x-auth-token
   - execution_id: path_execution_id

Response Parameters
-------------------

None

Response Example
----------------

.. literalinclude:: samples/executions/delete-execution-response.text
   :language: text
