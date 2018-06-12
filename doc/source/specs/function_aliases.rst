..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
Support Qinling function aliases
================================

https://storyboard.openstack.org/#!/story/2001588

Function aliases are like pointers to the specific function versions. By using
aliases, you can access the specific version of a function an alias is pointing
to (for example, to invoke the function) without having to know the specific
version the alias is pointing to. Function aliases enable the following use
cases:

- Easier support for promotion of new versions of functions and rollback when
  needed.

- Simplify management of event source mappings.


Problem description
===================

- As a function developer, you want to create an alias that points to function
  version, and remapping of aliases to different function versions.

- As an application developer who relies on the Qinling functions, I want a
  safe and sustainable way to call the functions without changing the
  applications after the function is updated.


Proposed change
===============

Data model impact
-----------------

A new database table needs to be created to store the mappings from alias to
function and function version.

REST API impact
---------------

* Create function alias that points to the specified function version. After
  creation, Qinling returns the function alias information, including
  function id, version id, alias name, description
  and timestamps.

  * POST ``/aliases``
  * Parameters: function_id
  * Parameters: description
  * Parameters: function_version
  * Parameters: name

    * the 'name' must be unique within the project

* Update function alias. Update the function id and version to which the alias
  points and alias description.

  * PUT ``/aliases/<alias_name>``
  * Parameters: function_id
  * Parameters: description
  * Parameters: function version

* Get the specified function alias information.

  * GET ``/aliases/<alias_name>``

* List the aliases.

  * GET ``/aliases/``

* Delete specific function alias. When deleting alias, need to check if there is
  any webhook/running job using the alias.

  * DELETE ``/aliases/<alias_name>``

* Create execution. Create execution with alias, so the execution will be
  created with the function id and version number the alias points to.

* Create job. Create job with alias, so the job will be created with the
  function id and version number the alias points to.

* Create webhook. Create webhook with alias, so the webhook will be
  created with the function id and version number the alias points to.

* Delete function. Qinling needs to check if there is any alias using that
  function, if there is alias associated with the function, the function
  deletion will fail.

* Delete function version. Qinling needs to check if there is any alias using that
  function version, if there is alias associated with the function version,
  the function version deleteion will fail.

End user impact
---------------

All the API changes should be supported in CLI.

Performance Impact
------------------

None

Deployer impact
---------------

Database migration script is provided.

Alternatives
------------

None


Implementation
==============

Assignee(s)
-----------

Dong Ma <winterma.dong@gmail.com>


Dependencies
============

None


Testing
=======

Pay attention to the notes written in ``REST API impact`` section.


References
==========

* Introduction to AWS Lambda Aliases
  https://docs.aws.amazon.com/lambda/latest/dg/aliases-intro.html
