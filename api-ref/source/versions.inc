.. -*- rst -*-
  
=========
 Versions
=========

Lists, creates, detaches, shows details and deletes versions.

Function versions are like git commits, they’re snapshots of your
project history. Each version has a number that serves as its ID,
starting with 1 and incrementing up, and never reused. The code for
a published version of a function is immutable (i.e. cannot be changed).
So, a version number corresponds to a specific set of function code with
certainty.


Create a version
================

.. rest_method:: POST /v1/functions/{function_id}/versions

Create a version. 

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
   - function_id: path_function_id
   - description: version_description

Request Example
---------------

.. literalinclude:: samples/versions/create-version-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - description: version_description
   - function_id: function_id
   - count: version_count
   - version_number: version_number
   - project_id: project_id
   - status: status
   - created_at: created_at
   - updated_at: updated_at


Response Example
----------------

.. literalinclude:: samples/versions/create-version-response.json
   :language: javascript


List versions
=============

.. rest_method:: GET /v1/functions/{function_id}/versions

List versions.

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
   - description: version_description
   - function_id: function_id
   - count: version_count
   - version_number: version_number
   - project_id: project_id
   - status: status
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/versions/list-versions-response.json
   :language: javascript


Show a version
==============

.. rest_method:: GET /v1/functions/{function_id}/versions/{version_number}

Show a version.

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
   - version_number: path_version_number

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - description: version_description
   - function_id: function_id
   - count: version_count
   - version_number: version_number
   - project_id: project_id
   - status: status
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/versions/show-version-response.json
   :language: javascript


Detach a version
================

.. rest_method:: POST /v1/functions/{function_id}/versions/{version_number}/detach

Detach a version.

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
   - version_number: path_version_number

Response Parameters
-------------------

None

Response Example
----------------


.. literalinclude:: samples/versions/detach-version-response.text
   :language: text


Delete a version
================

.. rest_method:: DELETE /v1/functions/{function_id}/versions/{version_number}

Delete a version.

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
   - version_number: path_version_number

Response Parameters
-------------------

None

Response Example
----------------

None
