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

Config Qinling with existing Kubernetes cluster
===============================================

In most cases, it's not ideal to set up a new dedicated Kubernetes cluster for
Qinling. The component which works with Kubernetes cluster in Qinling is the
``qinling-engine``. Follow the steps below to configure Qinling to work with an
existing Kubernetes cluster, and make Qinling access the Kubernetes API with
authentication and authorization.

Configurations
~~~~~~~~~~~~~~

Below are the options that relate to accessing the Kubernetes API in Qinling's
configuration file, all of them are under the ``kubernetes`` section.

.. code-block:: ini

    [kubernetes]
    kube_host = http://127.0.0.1:8001
    use_api_certificate = True
    ssl_ca_cert = /etc/qinling/pki/kubernetes/ca.crt
    cert_file = /etc/qinling/pki/kubernetes/qinling.crt
    key_file = /etc/qinling/pki/kubernetes/qinling.key

For now, just update the ``kube_host`` to the URI which the Kubernetes API
serves for HTTPS connections with authentication and authorization, for
example, ``kube_host = https://kube-api.example.com:6443``. We will cover the
other options in the following sections.

Authentication and Authorization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The access to the Kubernetes API is controlled by several modules, refer to
`Controlling Access to the Kubernetes API <https://kubernetes.io/docs/admin/accessing-the-api/>`_
for more details.

By default, Qinling engine is configured to access the Kubernetes API with
a client certificate for authentication(``use_api_certificate`` is set to
``True``), so make sure that the Kubernetes API server is running with the
``--client-ca-file=SOMEFILE`` option for client certificate authentication to
be enabled. The common name of the subject in the client certificate is used as
the user name for the requests that Qinling engine makes to the Kubernetes API
server. Refer to
`Authentication in Kubernetes <https://kubernetes.io/docs/admin/authentication/>`_.

If `RBAC Authorization <https://kubernetes.io/docs/admin/authorization/rbac/>`_
is enabled in the Kubernetes API, we will also have to grant access to resources
in Kubernetes for the specific user that Qinling uses to make requests to the
Kubernetes API. Using RBAC Authorization can ensure that Qinling access the
Kubernetes API with only the permission that it needs.

Generate Client Certificate for Qinling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See `Managing Certificates <https://kubernetes.io/docs/concepts/cluster-administration/certificates/>`_
for how to generate a client cert. We use ``cfssl`` as the example here.

#) Download and prepare the command line tools.

    .. code-block:: console

        curl -L https://pkg.cfssl.org/R1.2/cfssl_linux-amd64 -o /tmp/cfssl
        chmod +x /tmp/cfssl
        curl -L https://pkg.cfssl.org/R1.2/cfssljson_linux-amd64 -o /tmp/cfssljson
        chmod +x /tmp/cfssljson

#) Generate the client ceritificate for Qinling. Note that the common name
   of the subject is set to ``qinling`` in the example CSR located at
   ``example/kubernetes/cfssl-client-csr.json``.

    .. code-block:: console

        mkdir certs; cd certs
        /tmp/cfssl gencert -ca=/path/to/kubernetes_ca_crt \
            -ca-key=/path/to/kubernetes_ca_key \
            -config=QINLING_SOURCE/example/kubernetes/cfssl-ca-config.json \
            -profile=client \
            QINLING_SOURCE/example/kubernetes/cfssl-client-csr.json | /tmp/cfssljson -bare client

#) Copy the needed files to the locations. The command above generates two
   files named ``client-key.pem`` and ``client.pem``, the former is the key
   file of the client certificate, and the latter is the certificate file
   itself.

    .. code-block:: console

        mkdir -p /etc/qinling/pki/kubernetes
        cp client-key.pem /etc/qinling/pki/kubernetes/qinling.key
        cp client.pem /etc/qinling/pki/kubernetes/qinling.crt
        cp /path/to/kubernetes_ca_crt /etc/qinling/pki/kubernetes/ca.crt

   .. note::

      Make sure both ``/etc/qinling/pki/kubernetes`` and ``/etc/qinling/pki``
      belong to Qinling service user. You can set the permissions with
      ``chown -R qinling:qinling /etc/qinling/pki``

Create Role and RoleBinding in Kubernetes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If RBAC Authorization is enabled, we can limit the permissions that Qinling
access the Kubernetes API. Before you procceed the steps in this section,
make sure that the Kubernetes API server is running with the
``--authorization-mode=RBAC`` option.

Qinling provides a single file located at
``example/kubernetes/k8s_qinling_role.yaml`` for users to
create a ``Role`` and a ``ClusterRole`` with the permissions that Qinling
needs, and bind the roles to the user named ``qinling``, which is from
the common name of the subject in the client certificate. The role is defined
within a namespace named ``qinling``, which is the default namespace that
Qinling uses and the name is configurable.

#) Grant access to the resources in the Kubernetes cluster for Qinling. The
   following command can be running on any host that kubectl is installed
   to interact with Kubernetes.

    .. code-block:: console

        curl -sSL https://raw.githubusercontent.com/openstack/qinling/master/example/kubernetes/k8s_qinling_role.yaml | kubectl create -f -

The command above creates a ``ClusterRole`` named ``qinling`` with the
cluster-wide permissions that Qinling needs and binds it to the ``qinling``
user. It also creates a ``Role`` named ``qinling`` within a newly created
``qinling`` namespace and binds it to the specific user. So the access to
resources within that namespace is also granted.

Start Qinling Engine
~~~~~~~~~~~~~~~~~~~~

Start the qinling-engine service after the steps above are done. And now
Qinling is accessing the Kubernetes API with itself authenticated by a client
certificate. And the requests that Qinling makes to the Kubernetes API
are also authorized.

Access the Kubernetes API Insecurely (For Testing ONLY)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Qinling can also connect to the Kubernetes API insecurely if the Kubernetes API
server serves for insecure connections. However this is not recommended and
should be used for testing purpose only.

In the configuration file, under the ``kubernetes`` section, set ``kube_host``
to the URI which the Kubernetes API serves for insecure HTTP connections, for
example, ``kube_host = http://localhost:8080``, and set ``use_api_certificate``
to ``False`` to disable Qinling using a client certificate to access the
Kubernetes API.