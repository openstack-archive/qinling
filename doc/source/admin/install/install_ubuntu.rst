..
      Copyright 2018 Catalyst IT Ltd
      All Rights Reserved.
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

Install Qinling on Ubuntu 16.04
===============================

This section describes how to install and configure the Function management
service, code-named qinling on the controller node that runs Ubuntu 16.04 (LTS).

Prerequisites
-------------

Before you install and configure Qinling, you must create a database,
service credentials, and API endpoints.

#. To create the database, complete these steps:

   * Use the database access client to connect to the database
     server as the ``root`` user:

     .. code-block:: console

        # mysql -u root -p

   * Create the ``qinling`` database:

     .. code-block:: console

        CREATE DATABASE qinling;

   * Grant proper access to the ``qinling`` database:

     .. code-block:: console

        GRANT ALL PRIVILEGES ON qinling.* TO 'qinling'@'localhost' \
          IDENTIFIED BY 'QINLING_DBPASS';
        GRANT ALL PRIVILEGES ON qinling.* TO 'qinling'@'%' \
          IDENTIFIED BY 'QINLING_DBPASS';

     Replace ``QINLING_DBPASS`` with a suitable password.

   * Exit the database access client.

#. Source the ``admin`` credentials to gain access to
   admin-only CLI commands:

   .. code-block:: console

      $ . admin-openrc

#. To create the service credentials, complete these steps:

   * Create the ``qinling`` user:

     .. code-block:: console

        $ openstack user create --domain default --password-prompt qinling
        User Password:
        Repeat User Password:
        +---------------------+----------------------------------+
        | Field               | Value                            |
        +---------------------+----------------------------------+
        | domain_id           | default                          |
        | enabled             | True                             |
        | id                  | f77c97367087440da5f923bfcc66f68b |
        | name                | qinling                          |
        | options             | {}                               |
        | password_expires_at | None                             |
        +---------------------+----------------------------------+

   * Add the ``admin`` role to the ``qinling`` user:

     .. code-block:: console

        $ openstack role add --project service --user qinling admin

     .. note::

        This command provides no output.

   * Create the ``qinling`` service entities:

     .. code-block:: console

        $ openstack service create function-engine \
            --name qinling --description="Function Service"
        +-------------+----------------------------------+
        | Field       | Value                            |
        +-------------+----------------------------------+
        | description | Function Service                 |
        | enabled     | True                             |
        | id          | 8811fab348b548e3adef6ff0b149edfb |
        | name        | qinling                          |
        | type        | function-engine                  |
        +-------------+----------------------------------+

#. Create the Function engine service API endpoints:

   .. code-block:: console

      $ openstack endpoint create --region RegionOne \
          function-engine public http://controller:7070
      +--------------+----------------------------------+
      | Field        | Value                            |
      +--------------+----------------------------------+
      | enabled      | True                             |
      | id           | 70937a84ed434256b11853b7e8a05d91 |
      | interface    | public                           |
      | region       | RegionOne                        |
      | region_id    | RegionOne                        |
      | service_id   | 8811fab348b548e3adef6ff0b149edfb |
      | service_name | qinling                          |
      | service_type | function-engine                  |
      | url          | http://controller:7070           |
      +--------------+----------------------------------+
      $ openstack endpoint create --region RegionOne \
          function-engine internal http://controller:7070
      +--------------+----------------------------------+
      | Field        | Value                            |
      +--------------+----------------------------------+
      | enabled      | True                             |
      | id           | 7249f13c00cf4ca788da3df3fac9cfe2 |
      | interface    | internal                         |
      | region       | RegionOne                        |
      | region_id    | RegionOne                        |
      | service_id   | 8811fab348b548e3adef6ff0b149edfb |
      | service_name | qinling                          |
      | service_type | function-engine                  |
      | url          | http://controller:7070           |
      +--------------+----------------------------------+
      $ openstack endpoint create --region RegionOne \
          function-engine admin http://controller:7070
      +--------------+----------------------------------+
      | Field        | Value                            |
      +--------------+----------------------------------+
      | enabled      | True                             |
      | id           | 7726669d928d47198388c599bfcd62a5 |
      | interface    | admin                            |
      | region       | RegionOne                        |
      | region_id    | RegionOne                        |
      | service_id   | 8811fab348b548e3adef6ff0b149edfb |
      | service_name | qinling                          |
      | service_type | function-engine                  |
      | url          | http://controller:7070           |
      +--------------+----------------------------------+

Install and configure Qinling components
----------------------------------------

#. Create qinling user and necessary directories:

   * Create user:

     .. code-block:: console

        # groupadd --system qinling
        # useradd --home-dir "/var/lib/qinling" \
              --create-home \
              --system \
              --shell /bin/false \
              -g qinling \
              qinling

   * Create directories:

     .. code-block:: console

        # mkdir -p /etc/qinling /var/lib/qinling/package
        # chown -R qinling:qinling /etc/qinling /var/lib/qinling/package

#. Clone and install qinling:

   .. code-block:: console

      # apt install -y python-pip
      # cd /var/lib/qinling
      # git clone https://git.openstack.org/openstack/qinling.git
      # chown -R qinling:qinling qinling
      # cd qinling
      # pip install -e .

#. Generate a sample configuration file:

   .. code-block:: console

      # su -s /bin/sh -c "oslo-config-generator \
          --config-file tools/config/config-generator.qinling.conf \
          --output-file etc/qinling.conf.sample" qinling
      # su -s /bin/sh -c "cp etc/qinling.conf.sample \
          /etc/qinling/qinling.conf" qinling
      # su -s /bin/sh -c "cp etc/policy.json.sample \
          /etc/qinling/policy.json" qinling

#. Edit the ``/etc/qinling/qinling.conf``:

   * In the ``[DEFAULT]`` section,
     configure ``RabbitMQ`` message queue access:

     .. code-block:: ini

        [DEFAULT]
        ...
        transport_url = rabbit://openstack:RABBIT_PASS@controller:5672/

     Replace ``RABBIT_PASS`` with the password you chose for the
     ``openstack`` account in ``RabbitMQ``.

   * In the ``[api]`` section, configure the IP address that Qinling API
     server is going to listen:

     .. code-block:: ini

        [api]
        ...
        host = 10.0.0.9
        port = 7070

     Replace ``10.0.0.9`` with the management interface IP address
     of the controller node if different.

   * In the ``[database]`` section, configure database access:

     .. code-block:: ini

        [database]
        ...
        connection = mysql+pymysql://qinling:QINLING_DBPASS@controller/qinling?charset=utf8

     Replace ``QINLING_DBPASS`` with the password you chose for
     the qinling database.

   * In the ``[storage]`` section, configure function package storage path:

     .. code-block:: ini

        [storage]
        ...
        file_system_dir = /var/lib/qinling/package

   * In the ``[oslo_policy]`` section, configure the policy file path for
     Qinling service:

     .. code-block:: ini

        [oslo_policy]
        ...
        policy_file = /etc/qinling/policy.json

   * In the ``[keystone_authtoken]`` section, configure
     Identity service access:

     .. code-block:: ini

        [keystone_authtoken]
        ...
        memcached_servers = controller:11211
        www_authenticate_uri = http://controller:5000
        project_domain_name = default
        project_name = service
        user_domain_name = default
        password = QINLING_PASS
        username = qinling
        auth_url = http://controller:5000
        auth_type = password
        auth_version = v3

     Replace QINLING_PASS with the password you chose for the qinling user in
     the Identity service.

   .. note::

      Make sure that ``/etc/qinling/qinling.conf`` still have the correct
      permissions. You can set the permissions again with:

      # chown qinling:qinling /etc/qinling/qinling.conf

#. Populate Qinling database:

   .. code-block:: console

      # su -s /bin/sh -c "qinling-db-manage --config-file \
          /etc/qinling/qinling.conf upgrade head" qinling

Install and configure Kubernetes and etcd
-----------------------------------------

Installing Kubernetes in not in the scope of this guide, you can refer to
`Kubernetes installation guide <https://kubernetes.io/docs/setup/>`_ for more
information.

For etcd installation, you can refer to
`OpenStack Installation Guide <https://docs.openstack.org/install-guide/environment-etcd.html>`_.

Qinling could also connect with existing kubernetes and etcd services,
`here <https://docs.openstack.org/qinling/latest/admin/install/config_kubernetes.html>`_
is the guide for the detailed configuration.

Finalize installation
---------------------

#. Create an upstart config for qinling-api, it could be named as
   ``/etc/systemd/system/qinling-api.service``:

   .. code-block:: bash

      cat <<EOF > /etc/systemd/system/qinling-api.service
      [Unit]
      Description = OpenStack Function Management Service API

      [Service]
      ExecStart = /usr/local/bin/qinling-api
      User = qinling

      [Install]
      WantedBy = multi-user.target
      EOF

#. Create an upstart config for qinling-engine, it could be named as
   ``/etc/systemd/system/qinling-engine.service``:

   .. code-block:: bash

      cat <<EOF > /etc/systemd/system/qinling-engine.service
      [Unit]
      Description = OpenStack Function Management Service Engine

      [Service]
      ExecStart = /usr/local/bin/qinling-engine
      User = qinling

      [Install]
      WantedBy = multi-user.target
      EOF

#. Enable and start qinling-api and qinling-engine:

   .. code-block:: console

      # systemctl enable qinling-api
      # systemctl enable qinling-engine

   .. code-block:: console

      # systemctl start qinling-api
      # systemctl start qinling-engine

#. Verify that qinling-api and qinling-engine services are running:

   .. code-block:: console

      # systemctl status qinling-api
      # systemctl status qinling-engine
