.. qinling documentation master file, created by
   sphinx-quickstart on Tue Jul  9 22:26:36 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Qinling's documentation!
===================================

.. note::

   Qinling (is pronounced "tʃinliŋ") refers to Qinling Mountains in southern
   Shaanxi Province in China. The mountains provide a natural boundary between
   North and South China and support a huge variety of plant and wildlife, some
   of which is found nowhere else on Earth.

Qinling is an OpenStack project to provide "Function as a service". This
project aims to provide a platform to support serverless functions (like AWS
Lambda). Qinling supports different container orchestration platforms
(Kubernetes/Swarm, etc.) and different function package storage backends
(local/Swift/S3) by nature using plugin mechanism.

With Qinling, you can run code without provisioning or managing servers. You
pay only for the compute time you consume—there's no charge when your code
isn't running. You can run code for virtually any type of application or
backend service—all with zero administration. Just upload your code and Qinling
takes care of everything required to run and scale your code with high
availability. You can set up your code to automatically trigger from other
OpenStack services or call it directly from any web or mobile app.

* Free software: Apache license
* Documentation: https://docs.openstack.org/qinling/latest/
* Source: http://git.openstack.org/cgit/openstack/qinling
* Features: https://storyboard.openstack.org/#!/project/927
* Bug Track: https://storyboard.openstack.org/#!/project/927
* IRC channel on Freenode: #openstack-qinling


Overview
--------

.. toctree::
   :maxdepth: 2

   quick_start
   glossary
   features
   videos

Administration/Operation Guide
------------------------------

.. toctree::
   :maxdepth: 2

   admin/index

CLI Guide
---------

.. toctree::
   :maxdepth: 2

   cli/index

Contributor/Developer Guide
---------------------------

.. toctree::
   :maxdepth: 2

   contributor/index
   specs/index

User Guide
----------

.. toctree::
   :maxdepth: 2

   user/index

Function Programming Guide
--------------------------

.. toctree::
   :maxdepth: 2

   function_developer/index

Indices and tables
------------------

* :ref:`genindex`
* :ref:`search`
