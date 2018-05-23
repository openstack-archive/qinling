..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
Support Qinling function versioning
===================================

https://storyboard.openstack.org/#!/story/2001587

Function versions are like git commits, they're snapshots of your project
history. Each version has a number that serves as its ID, starting with 1 and
incrementing up, and never reused. The code for a published version of a
function is immutable (i.e. cannot be changed). So, a version number
corresponds to a specific set of function code with certainty. With function
versioning, users can get the following benefits:

- Update the function code without breaking the existing applications that rely
  on the function.

- Easy to backup/restore different versions of code for the same function.


Problem description
===================

- As a function developer, I want to keep the existing code when I update the
  function so that it is easy to restore when something is wrong during the
  testing.

- As an application developer who relies on the Qinling functions, I want a
  safe and sustainable way to call the functions without changing the
  applications after the function is updated.


Proposed change
===============

Data model impact
-----------------

A new database table needs to be created to store the mappings from function
to its versions and locations. There may be different function versions that
stored in the same location, e.g. when user creates a new version but without
any function code change, the previous function version location will be
reused to save the storage space.

A new field is added to execution table, job table and webhook table denoting
which function version the execution or job is using, 0 means using the latest
version.

REST API impact
---------------

* Create function version. After creation, Qinling returns the function version
  information, including function id, version uuid, version sequence
  number(starting from 1), description and timestamps.

  * POST ``/functions/<function-id>/versions``
  * Parameters: description

* Update function version. Only updating description is allowed for now.

  * PUT ``/functions/<function_id>/versions/<version_id>``
  * Parameters: description

* Get function versions.

  * GET ``/functions/<function_id>/versions/``

* Get/Download specific function version. We use version sequence number
  instead of version uuid because it makes much more sense to end user. The
  version uuid may be used internally.

  * GET ``/functions/<function_id>/versions/<version_sequence_number>``
  * GET ``/functions/<function_id>/versions/<version_sequence_number>?download=true``

* Delete specific function version. Function version can be deleted only if
  there is no corresponding execution running and no association with running
  jobs and webhooks. If the function version code location is shared with
  others, do not delete the function version package.

  * DELETE ``/functions/<function_id>/versions/<version_id>``

* Create execution. Version sequence number needs to be specified when
  executing the function, latest version is used by default.

* Create job. Version sequence number needs to be specified when creating the
  job, latest version is used by default.

* Create webhook. Version sequence number needs to be specified when creating
  the webhook, latest version is used by default.

* Delete function. Qinling needs to support to delete the function with all its
  versions.

* Download function package API is still support, but only for latest function
  version.

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

Lingxian Kong <anlin.kong@gmail.com>


Dependencies
============

None


Testing
=======

Pay attention to the notes written in ``REST API impact`` section.


References
==========

* Introduction to AWS Lambda Versioning
  https://docs.aws.amazon.com/lambda/latest/dg/versioning-intro.html

* AWS Lambda Versioning Strategies
  https://medium.com/@kevinng/aws-lambda-versioning-strategies-5ef877efd0be
