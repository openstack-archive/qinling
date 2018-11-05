..
      Copyright 2017 Catalyst IT Ltd
      All Rights Reserved.
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

Setting up a development environment with devstack
==================================================

This page describes how to set up a working development
environment that can be used in deploying qinling on latest releases
of Ubuntu. These instructions assume you are already familiar
with git. Refer to `Getting the code`_ for additional information.

.. _Getting the code: http://wiki.openstack.org/GettingTheCode

Following these instructions will allow you to have a fully functional qinling
environment using the devstack project (a shell script to build
complete OpenStack development environments) on Ubuntu 16.04.

Configuring devstack with Qinling
---------------------------------

Qinling can be enabled in devstack by using the plug-in based interface it
offers.

.. note::

   The following steps have been fully verified only on Ubuntu 16.04.

Start by cloning the devstack repository using a non-root user:

::

    git clone https://github.com/openstack-dev/devstack

Change to devstack directory:

::

    cd devstack/

Create the ``local.conf`` file with the following minimal devstack
configuration:

.. code-block:: ini

    [[local|localrc]]
    RECLONE=True
    enable_plugin qinling https://github.com/openstack/qinling

    LIBS_FROM_GIT=python-qinlingclient
    DATABASE_PASSWORD=password
    ADMIN_PASSWORD=password
    SERVICE_PASSWORD=password
    SERVICE_TOKEN=password
    RABBIT_PASSWORD=password
    LOGFILE=$DEST/logs/stack.sh.log
    LOG_COLOR=False
    LOGDAYS=1

    ENABLED_SERVICES=rabbit,mysql,key

.. end

Here are several things you could customize:

* For multiple network cards, you need to specify the kubernetes API server's
  advertise address manually.

   .. code-block:: console

       export EXTRA_KUBEADM_INIT_OPTS="--apiserver-advertise-address <default-host-ip>"

   .. end

* Devstack will set up a new kubernetes cluster and re-use etcd service inside
  the cluster for Qinling services, which means you don't need to add etcd to
  the enabled services list in the ``local.conf`` file.
* If you already have an existing kubernetes/etcd cluster, add
  ``QINLING_INSTALL_K8S=False`` to the ``local.conf`` file. You need to
  manually config Qinling services after devstack completes, go to
  `Config Qinling with existing Kubernetes cluster <https://docs.openstack.org/qinling/latest/admin/install/config_kubernetes.html>`_
  for more configuration details.
* If you want to interact with Qinling in Horizon dashboard, add the following
  line to the ``local.conf`` file.

    .. code-block:: console

        enable_plugin qinling-dashboard https://git.openstack.org/openstack/qinling-dashboard

    .. end

Running devstack
----------------

Run the ``stack.sh`` script:

::

    ./stack.sh

After it completes, verify qinling service is installed properly:

.. code-block:: console

    $ source openrc admin admin
    $ openstack service list
    +----------------------------------+----------+-----------------+
    | ID                               | Name     | Type            |
    +----------------------------------+----------+-----------------+
    | 59be2ecc8b8d4e61af184ea3495bf207 | qinling  | function-engine |
    | e5891d41a929402384ef00ce7135a16d | keystone | identity        |
    +----------------------------------+----------+-----------------+
    $ openstack runtime list --print-empty
    +----+------+-------+--------+-------------+------------+------------+------------+
    | Id | Name | Image | Status | Description | Project_id | Created_at | Updated_at |
    +----+------+-------+--------+-------------+------------+------------+------------+
    +----+------+-------+--------+-------------+------------+------------+------------+

.. end

Kubernetes Integration
----------------------

By default, Qinling uses Kubernetes as its orchestrator backend, so a k8s
all-in-one environment (and some other related tools, e.g. kubectl) is also
set up during devstack installation.

Qinling devstack script uses `kubeadm <https://kubernetes.io/docs/setup/independent/create-cluster-kubeadm/>`_
for Kubernetes installation, refer to ``tools/gate/kubeadm/setup_gate.sh`` for
more detailed information about Qinling devstack installation.