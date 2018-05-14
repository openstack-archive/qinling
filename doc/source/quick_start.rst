Quick Start
===========

Installation
~~~~~~~~~~~~

A fast and simple way to try Qinling is to create a Devstack environment
including all related components and dependencies of Qinling service. Please
refer to `Setting up a development environment with devstack`_ for how to
install Qinling service in OpenStack devstack environment.

Qinling is a FaaS implemented on top of container orchestration system such as
Kubernetes, Swarm, etc. Particularly, Kubernetes is a reference backend
considering its popularity. A kubernetes cluster and its command line tool
have been installed in the devstack environment.

Qinling can work with OpenStack Keystone for authentication, or it can work
without authentication at all. By default, authentication is enabled, set
``auth_enable = False`` to disable authentication.

.. _Setting up a development environment with devstack: https://docs.openstack.org/qinling/latest/contributor/development-environment-devstack.html


Getting started with Qinling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::

   Currently, you can interact with Qinling using python-qinlingclient or
   sending RESTful API directly. Both ways are described in this guide.
   ``httpie`` is a convenient tool to send HTTP request, it will be installed
   during following steps.

Log into the devstack host, we will create python runtime/function/execution
in the following steps.

#. (Optional) Prepare a docker image for a specific programming language. For
   your convenience, there is a pre-built image
   ``openstackqinling/python-runtime`` that you could directly use to create a
   Python runtime in Qinling. Refer to the
   `image creation guide <https://docs.openstack.org/qinling/latest/admin/runtime.html>`_
   for how to build your own runtime images to be used in Qinling.

#. Create Python runtime using admin credential. ``Runtime`` in Qinling is the
   environment in which the function is actually running, ``runtime`` is
   supposed to be created/deleted/updated only by cloud operator. After
   creation, check the runtime status until it's ``available`` before invoking
   any functions:

   .. code-block:: console

      $ pip install httpie
      $ cd $DEVSTACK_DIR && source openrc admin admin
      $ TOKEN=$(openstack token issue -f yaml -c id | awk '{print $2}')
      $ http POST http://localhost:7070/v1/runtimes name=python2.7 \
          image=openstackqinling/python-runtime X-Auth-Token:$TOKEN
      HTTP/1.1 201 Created
      Connection: keep-alive
      Content-Length: 246
      Content-Type: application/json
      Date: Mon, 11 Dec 2017 22:35:08 GMT

      {
          "created_at": "2017-12-11 22:35:08.660498",
          "description": null,
          "id": "601efeb8-3e41-4e5c-a12a-986dbda252e3",
          "image": "openstackqinling/python-runtime",
          "is_public": true,
          "name": "python2.7",
          "project_id": "ce157785ffb24b3c862720283be4dbc8",
          "status": "creating",
          "updated_at": null
      }
      $ http GET http://localhost:7070/v1/runtimes/601efeb8-3e41-4e5c-a12a-986dbda252e3 \
        X-Auth-Token:$TOKEN
      HTTP/1.1 200 OK
      Connection: keep-alive
      Content-Length: 298
      Content-Type: application/json
      Date: Mon, 11 Dec 2017 22:37:01 GMT

      {
          "created_at": "2017-12-11 22:35:09",
          "description": null,
          "id": "601efeb8-3e41-4e5c-a12a-986dbda252e3",
          "image": "openstackqinling/python-runtime",
          "is_public": true,
          "name": "python2.7",
          "project_id": "ce157785ffb24b3c862720283be4dbc8",
          "status": "available",
          "updated_at": "2017-12-11 22:35:13"
      }

   .. end

   Using CLI:

   .. code-block:: console

      $ cd $DEVSTACK_DIR && source openrc admin admin
      $ openstack runtime create openstackqinling/python-runtime --name python2.7
      +-------------+--------------------------------------+
      | Field       | Value                                |
      +-------------+--------------------------------------+
      | id          | 4866b566-2c9a-4f00-9665-7808f7d811f8 |
      | name        | python2.7                            |
      | image       | openstackqinling/python-runtime      |
      | status      | available                             |
      | description | None                                 |
      | project_id  | ce157785ffb24b3c862720283be4dbc8     |
      | created_at  | 2017-12-11 22:40:16                  |
      | updated_at  | None                                 |
      +-------------+--------------------------------------+

   .. end

   Record the runtime ID for the function invocation later on.

#. Create a customized Python function package:

   .. code-block:: console

      $ mkdir ~/qinling_test
      $ cat <<EOF > ~/qinling_test/github_test.py
      import requests
      def main(*args, **kwargs):
          r = requests.get('https://api.github.com/events')
          return len(r.json())
      if __name__ == '__main__':
          main()
      EOF
      $ cd ~/qinling_test && zip -r ~/qinling_test/github_test.zip ./*

   .. end

#. Create function:

   .. code-block:: console

      $ cd $DEVSTACK_DIR && source openrc demo demo
      $ runtime_id=601efeb8-3e41-4e5c-a12a-986dbda252e3
      $ TOKEN=$(openstack token issue -f yaml -c id | awk '{print $2}')
      $ http -f POST http://localhost:7070/v1/functions name=github_test \
          runtime_id=$runtime_id \
          code='{"source": "package"}' \
          entry='github_test.main' \
          package@~/qinling_test/github_test.zip \
          X-Auth-Token:$TOKEN
      HTTP/1.1 201 Created
      Connection: keep-alive
      Content-Length: 303
      Content-Type: application/json
      Date: Mon, 11 Dec 2017 23:20:26 GMT

      {
          "code": {
              "source": "package"
          },
          "count": 0,
          "created_at": "2017-12-11 23:20:26.600054",
          "description": null,
          "entry": "github_test.main",
          "id": "cdce13b0-55c9-4a06-a67a-1cd1fe1fb161",
          "name": "github_test",
          "project_id": "c2a457c46df64ed4adcb31fdc80052d4",
          "runtime_id": "601efeb8-3e41-4e5c-a12a-986dbda252e3"
      }

   .. end

   Using CLI:

   .. code-block:: console

      $ openstack function create --name github_test \
          --runtime $runtime_id \
          --entry github_test.main \
          --package ~/qinling_test/github_test.zip
      +-------------+--------------------------------------+
      | Field       | Value                                |
      +-------------+--------------------------------------+
      | id          | c9195311-9aa7-4748-bd4b-1b0f9c28d858 |
      | name        | github_test                          |
      | description | None                                 |
      | count       | 0                                    |
      | code        | {u'source': u'package'}              |
      | runtime_id  | 601efeb8-3e41-4e5c-a12a-986dbda252e3 |
      | entry       | github_test.main                     |
      | created_at  | 2017-12-11 23:21:21                  |
      | updated_at  | None                                 |
      +-------------+--------------------------------------+

   .. end

#. Invoke the function by specifying ``function_id``:

   .. code-block:: console

      $ http POST http://localhost:7070/v1/executions \
          function_id=c9195311-9aa7-4748-bd4b-1b0f9c28d858 \
          X-Auth-Token:$TOKEN
      HTTP/1.1 201 Created
      Connection: keep-alive
      Content-Length: 347
      Content-Type: application/json
      Date: Mon, 11 Dec 2017 23:26:11 GMT

      {
          "created_at": "2017-12-11 23:26:09",
          "description": null,
          "function_id": "c9195311-9aa7-4748-bd4b-1b0f9c28d858",
          "id": "c3d61744-254a-4f41-8e6d-9e7dc1eb6a24",
          "input": null,
          "result": "{\"duration\": 1.299, \"output\": 30}",
          "project_id": "c2a457c46df64ed4adcb31fdc80052d4",
          "status": "success",
          "sync": true,
          "updated_at": "2017-12-11 23:26:12"
      }


   .. end

   Using CLI:

   .. code-block:: console

      $ openstack function execution create c9195311-9aa7-4748-bd4b-1b0f9c28d858
      +-------------+--------------------------------------+
      | Field       | Value                                |
      +-------------+--------------------------------------+
      | id          | b7ffdd3a-a0a8-441b-874d-3b6dcf7446d9 |
      | function_id | c9195311-9aa7-4748-bd4b-1b0f9c28d858 |
      | description | None                                 |
      | input       | {}                                   |
      | result      | {"duration": 1.483, "output": 30}    |
      | status      | success                              |
      | sync        | True                                 |
      | created_at  | 2017-12-11 23:27:04                  |
      | updated_at  | 2017-12-11 23:27:05                  |
      +-------------+--------------------------------------+

   .. end

Now, you have defined your first Qinling function and have it invoked
on-demand. Have fun with Qinling!
