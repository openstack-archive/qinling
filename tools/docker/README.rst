Using Qinling with Docker
=========================

Docker containers provide an easy way to quickly deploy independent or
networked Qinling instances in seconds. This guide describes the process
to launch an all-in-one Qinling container.


Docker Installation
-------------------

The following links contain instructions to install latest Docker software:

* `Docker Engine <https://docs.docker.com/engine/installation/>`_
* `Docker Compose <https://docs.docker.com/compose/install/>`_


Build the Qinling Image Manually
--------------------------------

Execute the following command from the repository top-level directory::

  docker build -t qinling -f tools/docker/Dockerfile .

The Qinling Docker image has one build parameter:


Running Qinling using Docker Compose
------------------------------------

To launch Qinling in the single node configuration::

  docker-compose -f tools/docker/docker-compose/infrastructure.yaml \
               -f tools/docker/docker-compose/qinling-single-node.yaml \
               -p qinling up -d

To launch Qinling in the multi node configuration::

  docker-compose -f tools/docker/docker-compose/infrastructure.yaml \
               -f tools/docker/docker-compose/qinling-multi-node.yaml \
               -p qinling up -d

The `--build` option can be used when it is necessary to rebuild the image,
for example:

  docker-compose -f tools/docker/docker-compose/infrastructure.yaml \
               -f tools/docker/docker-compose/qinling-single-node.yaml \
               -p qinling up -d --build

Running the Qinling client from the Docker Compose container
------------------------------------------------------------

To run the qinling client against the server in the container using the client
present in the container:

  docker run -it qinling_qinling1 qinling runtime list

Configuring Qinling
-------------------

The Docker image contains the minimal set of Qinling configuration parameters
by default:

+--------------------+------------------+--------------------------------------+
|Name                |Default value     | Description                          |
+====================+==================+======================================+
|`MESSAGE_BROKER_URL`|rabbit://guest:gu\|The message broker URL                |
|                    |est@rabbitmq:5672 |                                      |
+--------------------+------------------+----------------------+---------------+
|`DATABASE_URL`      |sqlite:///qinling\|The database URL                      |
|                    |.db               |                                      |
+--------------------+------------------+----------------------+---------------+
|`UPGRADE_DB`        |false             |If the `UPGRADE_DB` equals `true`,    |
|                    |                  |a database upgrade will be launched   |
|                    |                  |before Qinling main process           |
+--------------------+------------------+----------------------+---------------+
|`QINLING_SERVER`    |all               |Specifies which qinling server to     |
|                    |                  |start by the launch script.           |
+--------------------+------------------+----------------------+---------------+
|`LOG_DEBUG`         |false             |If set to true, the logging level will|
|                    |                  |be set to DEBUG instead of the default|
|                    |                  |INFO level.                           |
+--------------------+------------------+----------------------+---------------+

The `/etc/qinling/qinling.conf` configuration file can be mounted to the Qinling
Docker container by uncommenting and editing the `volumes` sections in the Qinling
docker-compose files.


Using Qinling Client
--------------------

The Qinling API will be accessible from the host machine on the default
port 7070. Install `python-qinlingclient` on the host machine to
execute qinling commands.
