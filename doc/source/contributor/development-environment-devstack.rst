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

This page describes how to setup a working development
environment that can be used in deploying qinling on latest releases
of Ubuntu. These instructions assume you are already familiar
with git. Refer to `Getting the code`_ for additional information.

.. _Getting the code: http://wiki.openstack.org/GettingTheCode

Following these instructions will allow you to have a fully functional qinling
environment using the devstack project (a shell script to build
complete OpenStack development environments) on Ubuntu 16.04.

Configuring devstack with qinling
---------------------------------

Qinling can be enabled in devstack by using the plug-in based interface it
offers.

.. note::

   The following steps have been fully verified only on Ubuntu 16.04.

Start by cloning the devstack repository:

::

    git clone https://github.com/openstack-dev/devstack

Change to devstack directory:

::

    cd devstack/

Copy the ``local.conf`` sample file to the upper level directory:

::

    cp samples/local.conf .

Enable the qinling plugin adding the following lines to the end of the
``local.conf`` file:

::

    ENABLED_SERVICES=rabbit,mysql,key,tempest
    enable_plugin qinling https://github.com/openstack/qinling
    LIBS_FROM_GIT="python-qinlingclient"

Running devstack
----------------

.. note::

   Before running devstack, make sure there is a loopback device defined in
   ``/etc/hosts`` file, ``127.0.1.1 localhost`` is recommended, any line
   including '127.0.0.1' will be deleted automatically during devstack running.

Run the ``stack.sh`` script:

::

    ./stack.sh

After it completes, verify qinling service is installed properly:

.. code-block:: console

    $ source openrc admin admin
    $ openstack service list
    +----------------------------------+----------+----------+
    | ID                               | Name     | Type     |
    +----------------------------------+----------+----------+
    | 60145bf464f943aa88613026bd6aa5e3 | qinling  | function |
    | 750ec7b067b7465bab2389e331f826de | keystone | identity |
    +----------------------------------+----------+----------+
    $ openstack runtime list --print-empty
    +----+------+-------+--------+-------------+------------+------------+------------+
    | Id | Name | Image | Status | Description | Project_id | Created_at | Updated_at |
    +----+------+-------+--------+-------------+------------+------------+------------+
    +----+------+-------+--------+-------------+------------+------------+------------+

Kubernetes Integration
----------------------

By default, Qinling uses Kubernetes as its orchestrator backend, so a k8s
all-in-one environment (and some other related tools, e.g. kubectl) is also
setup during devstack installation.

The idea and most of the scripts are coming from
`OpenStack-Helm <http://openstack-helm.readthedocs.io/en/latest/index.html>`_
project originally, but may be probably changed as the project evolving in
future.
