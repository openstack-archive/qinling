.. -*- rst -*-
  
=========
 Runtimes
=========

Lists, creates, updates, shows details and deletes runtimes.

The runtime is programming language support. Each runtime is encapsulated
in a container image which is used for creating the runtime container.
Qinling communicates with the container by sending HTTP requests and runs
user function inside.


Create a runtime
================

.. rest_method:: POST /v1/runtimes

Create a runtime.

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
   - name: runtime_name
   - image: runtime_image
   - description: runtime_description
   - is_public: runtime_is_public
   - trusted: runtime_trusted

Request Example
---------------

.. literalinclude:: samples/runtimes/create-runtime-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - name: runtime_name
   - image: runtime_image
   - description: runtime_description
   - is_public: runtime_is_public
   - trusted: runtime_trusted
   - project_id: project_id
   - status: status
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/runtimes/create-runtime-response.json
   :language: javascript


List runtimes
=============

.. rest_method:: GET /v1/runtimes

List runtimes.

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
   - name: runtime_name
   - image: runtime_image
   - description: runtime_description
   - is_public: runtime_is_public
   - trusted: runtime_trusted
   - project_id: project_id
   - status: status
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/runtimes/list-runtimes-response.json
   :language: javascript


Show a runtime
==============

.. rest_method:: GET /v1/runtimes/{runtime_id}

Show a runtime.

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
   - runtime_id: path_runtime_id

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - name: runtime_name
   - image: runtime_image
   - description: runtime_description
   - is_public: runtime_is_public
   - trusted: runtime_trusted
   - project_id: project_id
   - status: status
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/runtimes/show-runtime-response.json
   :language: javascript


Show a runtime pool
===================

.. rest_method:: GET /v1/runtimes/{runtime_id}/pool

Show a runtime pool.

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
   - runtime_id: runtime_id

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - name: id
   - capacity: runtime_capacity

Response Example
----------------

.. literalinclude:: samples/runtimes/show-runtime-pool-response.json
   :language: javascript


Update a runtime
================

.. rest_method:: PUT /v1/runtimes/{runtime_id}

Update a runtime.

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
   - runtime_id: path_runtime_id
   - name: runtime_name_update
   - image: runtime_image_update
   - description: runtime_description

Request Example
---------------

.. literalinclude:: samples/runtimes/update-runtime-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - name: runtime_name
   - image: runtime_image
   - description: runtime_description
   - is_public: runtime_is_public
   - trusted: runtime_trusted
   - project_id: project_id
   - status: status
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/runtimes/update-runtime-response.json
   :language: javascript


Delete a runtime
================

.. rest_method:: DELETE /v1/runtimes/{runtime_id}

Delete a runtime.

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
   - runtime_id: path_runtime_id

Response Parameters
-------------------

None

Response Example
----------------

.. literalinclude:: samples/runtimes/delete-runtime-response.text
   :language: text
