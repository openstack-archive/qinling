.. -*- rst -*-
  
=====
 Jobs
=====

Lists, creates, updates, shows details and deletes jobs.

Jobs allows to run periodically functions based on time period.
Time period is based on cron syntax.


Create a job
============

.. rest_method:: POST /v1/jobs

Create a job.

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
   - name: job_name
   - function_id: job_function_id
   - function_alias: job_function_alias
   - function_version: job_function_version
   - function_input: job_input 
   - pattern: job_pattern
   - count: job_count

Request Example
---------------

.. literalinclude:: samples/jobs/create-job-request.json
   :language: javascript

.. literalinclude:: samples/jobs/create-job-alias-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - name: job_name
   - function_id: job_function_id
   - function_version: job_function_version
   - function_input: job_input 
   - pattern: job_pattern
   - count: job_count
   - first_execution_time: job_first_execution
   - next_execution_time: job_next_execution
   - status: status
   - project_id: project_id
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/jobs/create-job-response.json
   :language: javascript


List jobs
=========

.. rest_method:: GET /v1/jobs

List jobs.

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
   - name: job_name
   - function_id: job_function_id
   - function_version: job_function_version
   - function_input: job_input 
   - pattern: job_pattern
   - count: job_count
   - first_execution_time: job_first_execution
   - next_execution_time: job_next_execution
   - status: status
   - project_id: project_id
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/jobs/list-jobs-response.json
   :language: javascript


Show a job
==========

.. rest_method:: GET /v1/jobs/{job_id}

Show a job.

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
   - job_id: path_job_id

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - name: job_name
   - function_id: job_function_id
   - function_version: job_function_version
   - function_input: job_input 
   - pattern: job_pattern
   - count: job_count
   - first_execution_time: job_first_execution
   - next_execution_time: job_next_execution
   - status: status
   - project_id: project_id
   - created_at: created_at
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/jobs/show-job-response.json
   :language: javascript


Update a job
============

.. rest_method:: PUT /v1/jobs/{job_id}

Update a job.

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
   - job_id: path_job_id

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - id: id
   - name: job_name
   - function_input: job_input
   - pattern: job_pattern_update
   - next_execution_time: job_next_execution_update
   - status: job_status_update

Request Example
---------------

.. literalinclude:: samples/jobs/update-job-request.json
   :language: javascript

Response Example
----------------

.. literalinclude:: samples/jobs/update-job-response.json
   :language: javascript


Delete a job
============

.. rest_method:: DELETE /v1/jobs/{job_id}

Delete a job.

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
   - job_id: path_job_id

Response Parameters
-------------------

None

Response Example
----------------

.. literalinclude:: samples/jobs/delete-job-response.text
   :language: text
