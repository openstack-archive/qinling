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

Config Qinling with existing kubernetes/etcd cluster
====================================================

In most cases, it's not ideal to set up a new dedicated kubernetes cluster for
Qinling. The component which works with kubernetes cluster in Qinling is the
``qinling-engine``. Follow the steps below to configure Qinling to work with
existing kubernetes/etcd cluster, and make Qinling access the kubernetes/etcd
service with authentication and authorization.

Prerequisites
~~~~~~~~~~~~~

* You know the kubernetes API address and etcd service address, for example:

  .. code-block:: console

      K8S_ADDRESS=10.0.0.5
      ETCD_ADDRESS=10.0.0.6

  .. end

* You have CA certificates of the kubernetes and etcd respectively and store on
  the host that ``qinling-engine`` is running.

  .. code-block:: console

      K8S_CA_CERT=$HOME/ca.crt
      K8S_CA_KEY=$HOME/ca.key
      ETCD_CA_CERT=$HOME/etcd_ca.crt
      ETCD_CA_KEY=$HOME/etcd_ca.key

  .. end

* This guide assumes
  `RBAC <https://kubernetes.io/docs/admin/authorization/rbac/>`_ is enabled in
  the kubernetes cluster.

Qinling configurations
~~~~~~~~~~~~~~~~~~~~~~

Below are the options and their default values that relate to accessing the
Kubernetes API and etcd in Qinling's configuration file.

.. code-block:: ini

    [kubernetes]
    kube_host = https://127.0.0.1:8001
    use_api_certificate = True
    ssl_ca_cert = /etc/qinling/pki/kubernetes/ca.crt
    cert_file = /etc/qinling/pki/kubernetes/qinling.crt
    key_file = /etc/qinling/pki/kubernetes/qinling.key

    [etcd]
    host = 127.0.0.1
    port = 2379
    protocol = https
    ca_cert = /etc/qinling/pki/etcd/ca.crt
    cert_file = /etc/qinling/pki/etcd/qinling-etcd-client.crt
    cert_key = /etc/qinling/pki/etcd/qinling-etcd-client.key

.. end

Change the kubernetes and etcd service addresses:

.. code-block:: ini

    [kubernetes]
    kube_host = https://${K8S_ADDRESS}:6443
    ...
    [etcd]
    host = ${ETCD_ADDRESS}
    ...

.. end

Generate and config client certificates for Qinling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are a lot of
`tools <https://kubernetes.io/docs/concepts/cluster-administration/certificates/>`_
out there for certificate generation. We use ``cfssl`` as the example here.

#) Download and prepare the command line tools as needed.

    .. code-block:: console

        curl -L https://pkg.cfssl.org/R1.2/cfssl_linux-amd64 -o /tmp/cfssl
        chmod +x /tmp/cfssl
        curl -L https://pkg.cfssl.org/R1.2/cfssljson_linux-amd64 -o /tmp/cfssljson
        chmod +x /tmp/cfssljson

    .. end

#) Generate the kubernetes and etcd client certificates for Qinling.

    .. code-block:: console

        mkdir -p /tmp/certs; cd /tmp/certs
        curl -SL https://raw.githubusercontent.com/openstack/qinling/master/example/kubernetes/cfssl-ca-config.json -o /tmp/certs/cfssl-ca-config.json
        curl -SL https://raw.githubusercontent.com/openstack/qinling/master/example/kubernetes/cfssl-client-csr.json -o /tmp/certs/cfssl-client-csr.json
        /tmp/cfssl gencert -ca=${K8S_CA_CERT} \
            -ca-key=${K8S_CA_KEY} \
            -config=/tmp/certs/cfssl-ca-config.json \
            -profile=client \
            /tmp/certs/cfssl-client-csr.json | /tmp/cfssljson -bare k8s-client
        /tmp/cfssl gencert -ca=${ETCD_CA_CERT} \
            -ca-key=${ETCD_CA_KEY} \
            -config=/tmp/certs/cfssl-ca-config.json \
            -profile=client \
            /tmp/certs/cfssl-client-csr.json | /tmp/cfssljson -bare etcd-client

    .. end

#) Move the certificates to the appropriate folders and ensure the qinling
   service user has permission to those folders.

    .. code-block:: console

        mkdir -p /etc/qinling/pki/{kubernetes,etcd}
        cp k8s-client-key.pem /etc/qinling/pki/kubernetes/qinling.key
        cp k8s-client.pem /etc/qinling/pki/kubernetes/qinling.crt
        cp etcd-client-key.pem /etc/qinling/pki/etcd/qinling-etcd-client.key
        cp etcd-client.pem /etc/qinling/pki/etcd/qinling-etcd-client.crt
        cp ${K8S_CA_CERT} /etc/qinling/pki/kubernetes/ca.crt
        cp ${ETCD_CA_CERT} /etc/qinling/pki/etcd/ca.crt
        chown -R qinling:qinling /etc/qinling/pki

    .. end

Create Role and RoleBinding in Kubernetes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

According least privilege principle, the operation permission of qinling user
in kubernetes cluster should be limited, this could be easily achieved by
applying the pre-defined authorization manifest file.

.. code-block:: console

    curl -sSL https://raw.githubusercontent.com/openstack/qinling/master/example/kubernetes/k8s_qinling_role.yaml | kubectl apply -f -

.. end

Restart qinling-engine service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Restart the ``qinling-engine`` service after the steps above are done, and now
Qinling is accessing the Kubernetes API and etcd service using TLS. The
requests that Qinling makes to the Kubernetes API are also authorized.

.. code-block:: console

    systemctl restart devstack@qinling-engine.service

.. end

Access the Kubernetes API Insecurely (For testing purpose ONLY)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Qinling can also connect to the Kubernetes API insecurely if the Kubernetes API
server serves for insecure connections. However, this is not recommended and
should be used for testing purpose only.

In the configuration file, under the ``kubernetes`` section, set ``kube_host``
to the URI which the Kubernetes API serves for insecure HTTP connections, for
example, ``kube_host = http://localhost:8080``, and set ``use_api_certificate``
to ``False`` to disable Qinling using a client certificate to access the
Kubernetes API.

.. code-block:: ini

    [kubernetes]
    kube_host = http://localhost:8080
    use_api_certificate = False

.. end
