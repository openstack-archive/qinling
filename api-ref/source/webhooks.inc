.. -*- rst -*-
  
=========
 Webhooks
=========

Lists, creates, updates, shows details and deletes webhooks.

Webhooks are a low-effort way to invoke the functions. They do not
require a bot user or authentication to use.


Create a webhook
================

.. rest_method:: POST /v1/webhooks

Create a webhook.

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
   - function_id: webhook_function_id
   - function_alias: webhook_function_alias
   - function_version: webhook_function_version
   - description: webhook_description

Request Example
---------------

.. literalinclude:: samples/webhooks/create-webhook-request.json
   :language: javascript

.. literalinclude:: samples/webhooks/create-webhook-alias-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - description: webhook_description
   - function_id: webhook_function_id
   - version_number: webhook_function_version
   - webhook_url: webhook_url
   - project_id: project_id
   - created_at: created_at
   - updated_at: updated_at


Response Example
----------------

.. literalinclude:: samples/webhooks/create-webhook-response.json
   :language: javascript


List webhooks
=============

.. rest_method:: GET /v1/webhooks

List webhooks.

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
   - description: webhook_description
   - function_id: webhook_function_id
   - version_number: webhook_function_version
   - webhook_url: webhook_url
   - project_id: project_id
   - created_at: created_at
   - updated_at: updated_at


Response Example
----------------

.. literalinclude:: samples/webhooks/list-webhooks-response.json
   :language: javascript


Show a webhook
==============

.. rest_method:: GET /v1/webhooks/{webhook_id}

Show a webhook.

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
   - webhook_id: path_webhook_id

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - description: webhook_description
   - function_id: webhook_function_id
   - version_number: webhook_function_version
   - webhook_url: webhook_url
   - project_id: project_id
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/webhooks/show-webhook-response.json
   :language: javascript


Update a webhook
================

.. rest_method:: PUT /v1/webhooks/{webhook_id}

Update a webhook.

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
   - webhook_id: path_webhook_id
   - function_id: webhook_function_id
   - function_alias: webhook_function_alias
   - function_version: webhook_function_version
   - description: webhook_description

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - description: webhook_description
   - function_id: webhook_function_id
   - version_number: webhook_function_version
   - webhook_url: webhook_url
   - project_id: project_id
   - created_at: created_at
   - updated_at: updated_at

Request Example
---------------

.. literalinclude:: samples/webhooks/update-webhook-request.json
   :language: javascript

.. literalinclude:: samples/webhooks/update-webhook-alias-request.json
   :language: javascript

Response Example
----------------

.. literalinclude:: samples/webhooks/update-webhook-response.json
   :language: javascript


Delete a webhook
================

.. rest_method:: DELETE /v1/webhooks/{webhook_id}

Delete a webhook.

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
   - webhook_id: path_webhook_id

Response Parameters
-------------------

None

Response Example
----------------

.. literalinclude:: samples/webhooks/delete-webhook-response.text
   :language: text
