.. -*- rst -*-
  
========
 Aliases
========

Lists, creates, updates, shows details and deletes aliases.

Function aliases are like pointers to the specific function versions.
By using aliases, you can access the specific version of a function an
alias is pointing to without having to know the specific version the alias
is pointing to.


Create an alias
===============

.. rest_method:: POST /v1/aliases

Create ana alias.

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
   - function_id: function_id
   - version: alias_version
   - description: alias_description

Request Example
---------------

.. literalinclude:: samples/aliases/create-alias-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - name: alias_name
   - description: alias_description
   - function_id: function_id
   - version_number: alias_version
   - project_id: project_id
   - status: status
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/aliases/create-alias-response.json
   :language: javascript


List aliases
============

.. rest_method:: GET /v1/aliases

List aliases.

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
   - name: alias_name
   - description: alias_description
   - function_id: function_id
   - version_number: alias_version
   - project_id: project_id
   - status: status
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/aliases/list-aliases-response.json
   :language: javascript


Show an alias
=============

.. rest_method:: GET /v1/aliases/{name}

Show an alias.

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
   - name: path_alias_name

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - name: alias_name
   - description: alias_description
   - function_id: function_id
   - version_number: alias_version
   - project_id: project_id
   - status: status
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/aliases/show-alias-response.json
   :language: javascript


Update an alias
===============

.. rest_method:: PUT /v1/aliases/{name}

Update an alias.

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
   - name: path_alias_name

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - name: alias_name
   - description: alias_description
   - function_id: function_id
   - version_number: alias_version
   - project_id: project_id
   - status: status
   - created_at: created_at
   - updated_at: updated_at

Request Example
---------------

.. literalinclude:: samples/aliases/update-alias-request.json
   :language: javascript

Response Example
----------------

.. literalinclude:: samples/aliases/update-alias-response.json
   :language: text


Delete an alias
===============

.. rest_method:: DELETE /v1/aliases/{name}

Delete an alias.

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
   - name: path_alias_name

Response Parameters
-------------------

None

Response Example
----------------

.. literalinclude:: samples/aliases/delete-alias-response.text
   :language: text
