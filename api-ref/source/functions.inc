.. -*- rst -*-
  
==========
 Functions
==========

Lists, creates, shows details for, downloads, detaches, updates,
scales and deletes functions.

Function contains the source code that will be executed into the runtime.
The source code langage within the function should match the runtime.


Create a function
=================

.. rest_method:: POST /v1/functions

Create a function.

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
   - name: function_name
   - description: function_description
   - runtime_id: function_runtime_id
   - code: function_code
   - entry: function_entry
   - cpu: function_cpu
   - memory: function_memory
   - timeout: function_timeout
   - package: function_package

Request Example
---------------

Package
#######

.. literalinclude:: samples/functions/create-function-package-request.json
   :language: javascript

.. literalinclude:: samples/functions/create-function-package-curl-request.text
   :language: text

Swift
#####

.. literalinclude:: samples/functions/create-function-swift-request.json
   :language: javascript

Image
#####

.. literalinclude:: samples/functions/create-function-image-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - name: function_name
   - description: function_description
   - runtime_id: function_runtime_id
   - code: function_code
   - entry: function_entry
   - cpu: function_cpu
   - memory: function_memory
   - timeout: function_timeout
   - package: function_package
   - latest_version: function_latest_version
   - count: function_count
   - project_id: project_id
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

Package
#######

.. literalinclude:: samples/functions/create-function-package-response.json
   :language: javascript

Swift
#####

.. literalinclude:: samples/functions/create-function-swift-response.json
   :language: javascript

Image
#####

.. literalinclude:: samples/functions/create-function-image-response.json
   :language: javascript


List functions
==============

.. rest_method:: GET /v1/functions

List functions.

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
   - name: function_name
   - description: function_description
   - runtime_id: function_runtime_id
   - code: function_code
   - count: function_count
   - cpu: function_cpu
   - memory: function_memory
   - entry: function_entry
   - timeout: function_timeout
   - project_id: project_id
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/functions/list-functions-response.json
   :language: javascript


Show a function
===============

.. rest_method:: GET /v1/functions/{function_id}

Show a function.

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
   - function_id: path_function_id

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - name: function_name
   - description: function_description
   - runtime_id: function_runtime_id
   - code: function_code
   - count: function_count
   - cpu: function_cpu
   - memory: function_memory
   - entry: function_entry
   - timeout: function_timeout
   - project_id: project_id
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/functions/show-function-response.json
   :language: javascript


Update a function
=================

.. rest_method:: PUT /v1/functions/{function_id}

Update a function.

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
   - function_id: path_function_id
   - name: function_name_update
   - description: function_description
   - runtime_id: function_runtime_id_update
   - code: function_code_update
   - entry: function_entry_update
   - cpu: function_cpu
   - memory: function_memory
   - timeout: function_timeout
   - package: function_package
   - count: function_count

Request Example
---------------

Package
#######

.. literalinclude:: samples/functions/update-function-package-request.json
   :language: javascript

.. literalinclude:: samples/functions/update-function-package-curl-request.text
   :language: text

Swift
#####

.. literalinclude:: samples/functions/update-function-swift-request.json
   :language: javascript

Image
#####

It is not possible to update an ``image`` function.

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - name: function_name
   - description: function_description
   - runtime_id: function_runtime_id
   - code: function_code
   - count: function_count
   - cpu: function_cpu
   - memory: function_memory
   - entry: function_entry
   - timeout: function_timeout
   - project_id: project_id
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

Package
#######

.. literalinclude:: samples/functions/update-function-package-response.json
   :language: javascript

Swift
#####

.. literalinclude:: samples/functions/update-function-swift-response.json
   :language: javascript

Image
#####

None


Download a function
===================

.. rest_method:: GET /v1/functions/{function_id}?download=true

Download a function.

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
   - function_id: path_function_id

Response Parameters
-------------------

None

Response Example
----------------

.. literalinclude:: samples/functions/download-function-response.text
   :language: text


Detach a function from a worker
===============================

.. rest_method:: POST /v1/functions/{function_id}/detach

Detach a function from a worker.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403

Request
-------

.. rest_parameters:: parameters.yaml

   - x-auth-token: x-auth-token
   - function_id: path_function_id

Response Parameters
-------------------

None

Response Example
----------------

.. literalinclude:: samples/functions/detach-function-response.text
   :language: text


Scale up a function
===================

.. rest_method:: POST /v1/functions/{function_id}/scale_up

Scale up a function.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403

Request
-------

.. rest_parameters:: parameters.yaml

   - x-auth-token: x-auth-token
   - function_id: path_function_id
   - count: function_scale_count_up

Response Parameters
-------------------

None

Response Example
----------------

.. literalinclude:: samples/functions/scaleup-function-response.text
   :language: text


Scale down a function
=====================

.. rest_method:: POST /v1/functions/{function_id}/scale_down

Scale down a function.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403

Request
-------

.. rest_parameters:: parameters.yaml

   - x-auth-token: x-auth-token
   - function_id: path_function_id
   - count: function_scale_count_down

Response Parameters
-------------------

None

Response Example
----------------

.. literalinclude:: samples/functions/scaledown-function-response.text
   :language: text


Delete a function
=================

.. rest_method:: DELETE /v1/functions/{function_id}

Delete a function.

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
   - function_id: path_function_id

Response Parameters
-------------------

None

Response Example
----------------

.. literalinclude:: samples/functions/delete-function-response.text
   :language: text
