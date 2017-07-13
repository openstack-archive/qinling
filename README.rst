=======
Qinling
=======

.. note::

   Qinling (is pronounced "tʃinliŋ") refers to Qinling Mountains in southern
   Shaanxi Province in China. The mountains provide a natural boundary between
   North and South China and support a huge variety of plant and wildlife, some
   of which is found nowhere else on Earth.

Qinling is Function as a Service for OpenStack. This project aims to provide a
platform to support serverless functions (like AWS Lambda). Qinling supports
different container orchestration platforms (Kubernetes/Swarm, etc.) and
different function package storage backends (local/Swift/S3) by nature using
plugin mechanism.

* Free software: Apache license
* Documentation: http://docs.openstack.org/developer/qinling
* Source: http://git.openstack.org/cgit/openstack/qinling
* Features: https://blueprints.launchpad.net/qinling
* Bugs: http://bugs.launchpad.net/qinling
* IRC channel: #openstack-qinling

Quick Start
~~~~~~~~~~~

Installation
------------

A fast and simple way to try Qinling is to create a Vagrant VM including all
related components and dependencies of Qinling service. For your convenience,
Qinling team already provide a Vagrantfile in ``tools/vagrant`` folder.

Qinling is a FaaS implemented on top of container orchestration system such as
Kubernetes, Swarm, etc. Particularly, Kubernetes is a reference backend
considering its popularity. So, you need to setup Kubernetes first before
installing Qinling. The easiest way to setup Kubernetes is to use `Minikube
<https://kubernetes.io/docs/getting-started-guides/minikube/>`_, it runs a
single-node Kubernetes cluster inside a VM alongside Qinling vagrant VM, so
they can communicate with each other without any network configuration.

.. note::

   In order to manage resources on Kubernetes, it is recommended to install
   `kubectl <https://kubernetes.io/docs/tasks/tools/install-kubectl/>`_
   command line tool.

Qinling can work with OpenStack Keystone for authentication, or it can work
without authentication at all. By default, authentication is disabled, config
``auth_enable = True`` to enable authentication.

After Kubernetes installation, perform the following commands on your local
host.

#. Setup HTTP proxy to access the Kubernetes API:

   .. code-block:: console

      $ kubectl proxy --accept-hosts='.*' --address='0.0.0.0'

      Starting to serve on [::]:8001

   .. end

#. Clone Qinling repo and go to ``vagrant`` directory:

   .. code-block:: console

      $ git clone https://github.com/LingxianKong/qinling.git
      $ cd qinling/tools/vagrant

   .. end

#. Modify Qinling sample config file according to your own environment. Suppose
   your IP address of your local host is ``192.168.200.50``, default Kubernetes
   API HTTP proxy port is ``8001``, and Qinling vagrant VM IP address is
   ``192.168.33.18`` (the default value in ``Vagrantfile``):

   .. code-block:: console

      $ sed -i 's/KUBERNETES_API_HOST/192.168.200.50/' qinling.conf.sample
      $ sed -i 's/KUBERNETES_API_PORT/8001/' qinling.conf.sample
      $ sed -i 's/QINLING_API_ADDRESS/192.168.33.18/' qinling.conf.sample

   .. end

#. Now, start Qinling vagrant VM:

   .. code-block:: console

      $ vagrant --version
      Vagrant 1.9.1
      $ vagrant up
      ...
      ==> default: INFO  [alembic.runtime.migration] Context impl MySQLImpl.
      ==> default: INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
      ==> default: INFO  [alembic.runtime.migration] Running upgrade  -> 001, Pike release

   .. end

   If you see message like the above, congratulations!

Getting started with Qinling
----------------------------

**Currently, you can interact with Qinling using python-qinlingclient or
sending RESTful API directly. Both ways are described in this guide.**

``httpie`` is a convenient tool to send HTTP request, make sure you installed
``httpie`` via ``pip install httpie`` before playing with Qinling.

If you prefer to use CLI, please make sure python-qinlingclient is installed.

Perform following commands on your local host, the process will create
runtime/function/execution in Qinling.

#. (Optional) Prepare a docker image including development environment for a
   specific programming language. For your convenience, I already build one
   (``lingxiankong/python-runtime``) in my docker hub account that you could
   directly use to create runtime in Qinling. Only ``Python 2`` runtime is
   supported for now, but it is very easy to add another program language
   support. If you indeed want to build a new image, run the following commands
   in ``qinling`` repo directory, replace ``DOCKER_USER`` with your own docker
   hub username:

   .. code-block:: console

      $ cd runtimes/python2
      $ docker build -t DOCKER_USER/python-runtime .
      $ docker push DOCKER_USER/python-runtime

   .. end

#. Create runtime. A runtime in Qinling is running environment for a specific
   language, this resource is supposed to be created/deleted/updated by cloud
   operator. After creation, check the runtime status is ``available``:

   .. code-block:: console

      $ http POST http://192.168.33.18:7070/v1/runtimes name=python2.7 \
        image=DOCKER_USER/python-runtime

      HTTP/1.1 201 Created
      Connection: keep-alive
      Content-Length: 194
      Content-Type: application/json
      Date: Fri, 12 May 2017 04:37:08 GMT

      {
          "created_at": "2017-05-12 04:37:08.129860",
          "id": "c1d78623-56bf-4487-9a72-1299b2c55e65",
          "image": "DOCKER_USER/python-runtime",
          "name": "python2.7",
          "project_id": "default",
          "status": "creating"
      }

      $ http GET http://192.168.33.18:7070/v1/runtimes/c1d78623-56bf-4487-9a72-1299b2c55e65

      HTTP/1.1 200 OK
      Connection: keep-alive
      Content-Length: 246
      Content-Type: application/json
      Date: Fri, 12 May 2017 04:37:50 GMT

      {
          "created_at": "2017-05-12 04:37:08",
          "description": null,
          "id": "c1d78623-56bf-4487-9a72-1299b2c55e65",
          "image": "DOCKER_USER/python-runtime",
          "name": "python2.7",
          "project_id": "default",
          "status": "available",
          "updated_at": "2017-05-12 04:37:08"
      }

   .. end

   Using CLI:

   .. code-block:: console

      $ openstack runtime create python2.7 DOCKER_USER/python-runtime
      +------------+--------------------------------------+
      | Field      | Value                                |
      +------------+--------------------------------------+
      | id         | c1d78623-56bf-4487-9a72-1299b2c55e65 |
      | name       | python2.7                            |
      | image      | DOCKER_USER/python-runtime           |
      | project_id | default                              |
      | status     | available                            |
      | created_at | 2017-05-12 04:37:08.129860           |
      | updated_at |                                      |
      +------------+--------------------------------------+

   .. end

#. Create a customized function package:

   .. code-block:: console

      $ mkdir ~/qinling_test
      $ cat <<EOF > ~/qinling_test/main.py
        import requests
        def main():
            r = requests.get('https://api.github.com/events')
            return len(r.json())
        if __name__ == '__main__':
            main()
        EOF
      $ pip install requests -t ~/qinling_test
      $ zip -r ~/qinling_test/qinling_test.zip ~/qinling_test/*

   .. end

#. Create function, ``runtime_id`` comes from the output of above command:

   .. code-block:: console

      $ http -f POST http://192.168.33.18:7070/v1/functions name=github_test \
        runtime_id=c1d78623-56bf-4487-9a72-1299b2c55e65 \
        code='{"package": "true"}' \
        package@~/qinling_test/qinling_test.zip

      HTTP/1.1 201 Created
      Connection: keep-alive
      Content-Length: 234
      Content-Type: application/json
      Date: Fri, 12 May 2017 04:49:59 GMT

      {
          "code": {
              "package": "true"
          },
          "created_at": "2017-05-12 04:49:59.659345",
          "description": null,
          "entry": "main.main",
          "id": "352e4c02-3c6b-4860-9b85-f72344b1f986",
          "name": "github_test",
          "runtime_id": "c1d78623-56bf-4487-9a72-1299b2c55e65"
      }

   .. end

   Using CLI:

   .. code-block:: console

      $ openstack function create github_test \
        c1d78623-56bf-4487-9a72-1299b2c55e65 \
        '{"source": "package"}' \
        --package ~/qinling_test/qinling_test.zip
      +------------+--------------------------------------+
      | Field      | Value                                |
      +------------+--------------------------------------+
      | id         | 352e4c02-3c6b-4860-9b85-f72344b1f986 |
      | name       | github_test                          |
      | count      | 0                                    |
      | code       | {u'source': u'package'}              |
      | runtime_id | c1d78623-56bf-4487-9a72-1299b2c55e65 |
      | entry      | main.main                            |
      | created_at | 2017-05-12 04:49:59.659345           |
      | updated_at |                                      |
      +------------+--------------------------------------+

   .. end

#. Invoke the function by specifying ``function_id``:

   .. code-block:: console

      $ http POST http://192.168.33.18:7070/v1/executions \
        function_id=352e4c02-3c6b-4860-9b85-f72344b1f986

      HTTP/1.1 201 Created
      Connection: keep-alive
      Content-Length: 255
      Content-Type: application/json
      Date: Thu, 11 May 2017 23:46:12 GMT

      {
          "created_at": "2017-05-12 04:51:10",
          "function_id": "352e4c02-3c6b-4860-9b85-f72344b1f986",
          "id": "80cd55be-d369-49b8-8bd5-e0bfc1d20d25",
          "input": null,
          "output": "{\"result\": 30}",
          "status": "success",
          "sync": true,
          "updated_at": "2017-05-12 04:51:23"
      }

   .. end

   Using CLI:

   .. code-block:: console

      $ openstack function execution create 352e4c02-3c6b-4860-9b85-f72344b1f986
      +-------------+------------------------------------------------------------+
      | Field       | Value                                                      |
      +-------------+------------------------------------------------------------+
      | id          | 80cd55be-d369-49b8-8bd5-e0bfc1d20d25                       |
      | function_id | 352e4c02-3c6b-4860-9b85-f72344b1f986                       |
      | input       | {}                                                         |
      | output      | {"result": {"duration": 1.2511260509490967, "output": 30}} |
      | status      | success                                                    |
      | sync        | True                                                       |
      | created_at  | 2017-05-12 04:51:10                                        |
      | updated_at  | 2017-05-12 04:51:23                                        |
      +-------------+------------------------------------------------------------+

   .. end

   If you invoke the same function again, you will find it is much faster
   thanks to Qinling cache mechanism.
