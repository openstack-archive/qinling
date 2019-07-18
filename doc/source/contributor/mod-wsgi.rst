..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.


============================
 Installing the API via WSGI
============================

This document provides two WSGI methods as examples:

* uWSGI
* Apache ``mod_wsgi``

.. seealso::

    https://governance.openstack.org/tc/goals/pike/deploy-api-in-wsgi.html#uwsgi-vs-mod-wsgi


The "wsgi.py" file
==================

``qinling/api/wsgi.py`` file sets up the API WSGI application, it has to be copied into ``/var/www/cgi-bin/qinling`` directory.

.. code-block:: console

   mkdir -p /var/www/cgi-bin/qinling
   cp qinling/api/wsgi.py /var/www/cgi-bin/qinling
   chown qinling:qinling -R /var/www/cgi-bin/qinling


Running with Apache and mod_wsgi
================================

The ``etc/apache2/qinling-api.conf`` file  contains an example
of Apache virtualhost configured with ``mod_wsgi``.

.. literalinclude:: ../../../etc/apache2/qinling-api.conf

1. On deb-based systems copy or symlink the file to
   ``/etc/apache2/sites-available``.

   For rpm-based systems the file will go in
   ``/etc/httpd/conf.d``.

2. Modify the ``WSGIDaemonProcess`` directive to set the ``user`` and
   ``group`` values to an appropriate user on your server. In many
   installations ``qinling`` will be correct. Modify the ``WSGIScriptAlias``
   directive to set the path of the wsgi script.

   If you are using a virtualenv ``WSGIDaemonProcess`` requires
   ``python-path`` parameter, the value should be
   ``<your-venv-path>/lib/python<your-version>/site-packages``.

3. Enable the ``qinling-api`` virtualhost.

   On deb-based systems:

   .. code-block:: console

      a2ensite qinling-api
      systemctl reload apache2

   On rpm-based systems:

   .. code-block:: console

      systemctl reload httpd


Running with uWSGI
==================

The ``etc/uwsgi/qinling-api.yaml`` file contains an example
of uWSGI configuration.

1. Create the ``qinling-api.yaml`` file.

   .. literalinclude:: ../../../etc/uwsgi/qinling-api.yaml

2. Then start the uWSGI server:

   .. code-block:: console

      uwsgi ./qinling-api.yaml

   Or start in background with:

   .. code-block:: console

      uwsgi -d ./qinling-api.yaml
