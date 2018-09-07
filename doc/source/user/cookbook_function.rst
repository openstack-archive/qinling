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

Function Cookbook
=================

Introduction
~~~~~~~~~~~~

Qinling function lets you execute your code in a serverless environment without
having to first create a VM or container. This cookbook contains several
examples for how to create functions in Qinling.

Examples
~~~~~~~~

Create Python function with libraries in a package
--------------------------------------------------

This guide describes how to create a python function with libraries in a
package and how to invoke the function in a Python runtime(the steps assume
there is already a Python 2.7 runtime available in the deployment).

The function resizes an image which stores in Swift and uploads the resized
image to a new container with a same object name. For the function to work, a
python library called ``Pillow`` needs to be installed together with the
function code, the ``python-swiftclient`` doesn't need to be installed because
Qinling supports it as a built-in library in Qinling's default Python 2.7
runtime implementation.

The function needs two positional parameters:

* ``container_name``: The container name in Swift that the original image file
  is stored in.
* ``object_name``: The object name in the container.

There is no output for the function itself, but you can check the function
execution log to see the whole process.

.. note::

  The following process has been tested in a Devstack environment in which
  Swift is also installed.

#. Create a directory, for example ``~/qinling_test``

   .. code-block:: console

      mkdir ~/qinling_test

   .. end

#. Write a custom python code for resizing an image at the root level of the
   directory created above.

   .. code-block:: console

      cat <<EOF > ~/qinling_test/resize_image.py
      import os

      from PIL import Image
      import swiftclient
      from swiftclient.exceptions import ClientException


      def resize_image(image_path, resized_path):
          with Image.open(image_path) as image:
              image.thumbnail(tuple(x / 4 for x in image.size))
              image.save(resized_path)


      def main(context, container_name, object_name):
          conn = swiftclient.Connection(
              session=context['os_session'],
              os_options={'region_name': 'RegionOne'},
          )

          # Download original image
          image_path = os.path.abspath('./%s' % object_name)
          _, obj_contents = conn.get_object(container_name, object_name)
          with open(image_path, 'w') as local:
              local.write(obj_contents)

          print('Downloaded object %s from container %s' % (object_name, container_name))

          thumb_path = os.path.abspath('./%s_resized.png' % object_name)
          resize_image(image_path, thumb_path)

          print('Resized.')

          # Create new container if needed
          new_container_name = '%s_resized' % container_name
          try:
              conn.head_container(new_container_name)
          except ClientException:
              conn.put_container(new_container_name)
              print("New container %s created." % new_container_name)

          # Upload resized image
          with open(thumb_path, 'r') as new_local:
              conn.put_object(
                  new_container_name,
                  object_name,
                  contents=new_local,
                  content_type='text/plain'
              )
          os.remove(image_path)
          os.remove(thumb_path)

          print('Uploaded object %s to container %s' % (object_name, new_container_name))
      EOF

   .. end

#. Install the python libraries necessary for the program execution using
   ``pip``. The libraries need to be installed at the root level of the
   directory.

   .. code-block:: console

      pip install module-name -t path/to/dir

   .. end

   In this example, we would install the library ``Pillow`` in the project
   directory.

   .. code-block:: console

      pip install Pillow -t ~/qinling_test

   .. end

   .. note::

      Qinling's default Python runtime includes most of the OpenStack project
      SDKs, so you don't need to include python-swiftclient in your function
      code package, but you can optionally include it for your local testing.

#. Add the contents of the whole directory to a zip file which is now your
   function code package. Make sure you zip the contents of the directory and
   not the directory itself.

   .. code-block:: console

      cd ~/qinling_test; zip -r9 ~/qinling_test/resize_image.zip .

   .. end

#. Create function and get the function ID, replace the ``runtime_id`` with
   the one in your deployment.

   .. code-block:: console

      runtime_id=601efeb8-3e41-4e5c-a12a-986dbda252e3
      openstack function create --name resize_image \
        --runtime $runtime_id \
        --entry resize_image.main \
        --package ~/qinling_test/resize_image.zip
      +-------------+-------------------------------------------------------------------------+
      | Field       | Value                                                                   |
      +-------------+-------------------------------------------------------------------------+
      | id          | f8b18de6-1751-46d6-8c0d-0f1ecf943d12                                    |
      | name        | resize_test                                                             |
      | description | None                                                                    |
      | count       | 0                                                                       |
      | code        | {u'source': u'package', u'md5sum': u'ae7ad9ae450a8c5c31dca8e96f42247c'} |
      | runtime_id  | 685c1e6c-e175-4b32-9ec4-244d39c1077e                                    |
      | entry       | resize_image.main                                                       |
      | project_id  | a1e58c83923a4e2ca9370df6007c7fe6                                        |
      | created_at  | 2018-07-03 04:38:50.147277                                              |
      | updated_at  | None                                                                    |
      | cpu         | 100                                                                     |
      | memory_size | 33554432                                                                |
      +-------------+-------------------------------------------------------------------------+
      function_id=f8b18de6-1751-46d6-8c0d-0f1ecf943d12

   .. end

#. Upload an image to Swift.

   .. code-block:: console

      curl -SL https://docs.openstack.org/arch-design/_images/osog_0001.png -o ~/origin.jpg
      openstack container create origin_folder
      +---------------------------------------+---------------+------------------------------------+
      | account                               | container     | x-trans-id                         |
      +---------------------------------------+---------------+------------------------------------+
      | AUTH_a1e58c83923a4e2ca9370df6007c7fe6 | origin_folder | tx664a23a4a6e345b6af30d-005b3b6127 |
      +---------------------------------------+---------------+------------------------------------+
      openstack object create origin_folder ~/origin.jpg --name image
      +--------+---------------+----------------------------------+
      | object | container     | etag                             |
      +--------+---------------+----------------------------------+
      | image  | origin_folder | 07855978284adfcbbf76954a7c654a74 |
      +--------+---------------+----------------------------------+
      openstack object show origin_folder image
      +----------------+---------------------------------------+
      | Field          | Value                                 |
      +----------------+---------------------------------------+
      | account        | AUTH_a1e58c83923a4e2ca9370df6007c7fe6 |
      | container      | origin_folder                         |
      | content-length | 45957                                 |
      | content-type   | application/octet-stream              |
      | etag           | 07855978284adfcbbf76954a7c654a74      |
      | last-modified  | Tue, 03 Jul 2018 11:44:33 GMT         |
      | object         | image                                 |
      +----------------+---------------------------------------+

   .. end

#. Invoke the function by specifying function_id and the function inputs as
   well.

   .. code-block:: console

      openstack function execution create $function_id --input '{"container_name": "origin_folder", "object_name": "image"}'
      +------------------+-------------------------------------------------------------+
      | Field            | Value                                                       |
      +------------------+-------------------------------------------------------------+
      | id               | 04c60ae7-08c9-454c-9b2c-0bbf36391159                        |
      | function_id      | d3de49fc-7488-4635-aa48-84e754881eb8                        |
      | function_version | 0                                                           |
      | description      | None                                                        |
      | input            | {"object_name": "image", "container_name": "origin_folder"} |
      | result           | {"duration": 2.74, "output": null}                          |
      | status           | success                                                     |
      | sync             | True                                                        |
      | project_id       | a1e58c83923a4e2ca9370df6007c7fe6                            |
      | created_at       | 2018-07-03 09:12:12                                         |
      | updated_at       | 2018-07-03 09:12:16                                         |
      +------------------+-------------------------------------------------------------+

   .. end

#. Check the function execution log.

   .. code-block:: console

      openstack function execution log show 04c60ae7-08c9-454c-9b2c-0bbf36391159
      Start execution: 04c60ae7-08c9-454c-9b2c-0bbf36391159
      Downloaded object image from container origin_folder
      Resized.
      New container origin_folder_resized created.
      Uploaded object image to container origin_folder_resized
      Finished execution: 04c60ae7-08c9-454c-9b2c-0bbf36391159

   .. end

#. Verify that a new object of smaller size was created in a new container in
   Swift.

   .. code-block:: console

      openstack container list
      +-----------------------+
      | Name                  |
      +-----------------------+
      | origin_folder         |
      | origin_folder_resized |
      +-----------------------+
      openstack object list origin_folder_resized
      +-------+
      | Name  |
      +-------+
      | image |
      +-------+
      openstack object show origin_folder_resized image
      +----------------+---------------------------------------+
      | Field          | Value                                 |
      +----------------+---------------------------------------+
      | account        | AUTH_a1e58c83923a4e2ca9370df6007c7fe6 |
      | container      | origin_folder_resized                 |
      | content-length | 31779                                 |
      | content-type   | text/plain                            |
      | etag           | f737cc7f0fe5c15d8a6897c8fe159c02      |
      | last-modified  | Tue, 03 Jul 2018 11:46:40 GMT         |
      | object         | image                                 |
      +----------------+---------------------------------------+

   .. end

   Pay attention to the object ``content-length`` value which is smaller than
   the original object.

Create a function stored in OpenStack Swift
-------------------------------------------

OpenStack object storage service, swift can be integrated with Qinling to
create functions. You can upload your function package to swift and create
the function by specifying the container name and object name in Swift. In this
example the function would return ``"Hello, World"`` by default, you can
replace the string with the function input. The steps assume there is already
a Python 2.7 runtime available in the deployment.

#. Create a function deployment package.

   .. code-block:: console

      mkdir ~/qinling_swift_test
      cd ~/qinling_swift_test
      cat <<EOF > hello_world.py
      def main(name='World',**kwargs):
          ret = 'Hello, %s' % name
          return ret
      EOF

      cd ~/qinling_swift_test && zip -r ~/qinling_swift_test/hello_world.zip ./*

   .. end

#. Upload the file to swift

   .. code-block:: console

      openstack container create functions

      +---------------------------------------+------------------+------------------------------------+
      | account                               | container        | x-trans-id                         |
      +---------------------------------------+------------------+------------------------------------+
      | AUTH_6ae7142bff0542d8a8f3859ffa184236 | functions        | 9b45bef5ab2658acb9b72ee32f39dbc8   |
      +---------------------------------------+------------------+------------------------------------+

      openstack object create functions hello_world.zip

      +-----------------+-----------+----------------------------------+
      | object          | container | etag                             |
      +-----------------+-----------+----------------------------------+
      | hello_world.zip | functions | 9b45bef5ab2658acb9b72ee32f39dbc8 |
      +-----------------+-----------+----------------------------------+

      openstack object show functions hello_world.zip

      +----------------+---------------------------------------+
      | Field          | Value                                 |
      +----------------+---------------------------------------+
      | account        | AUTH_6ae7142bff0542d8a8f3859ffa184236 |
      | container      | functions                             |
      | content-length | 246                                   |
      | content-type   | application/zip                       |
      | etag           | 9b45bef5ab2658acb9b72ee32f39dbc8      |
      | last-modified  | Wed, 18 Jul 2018 17:45:23 GMT         |
      | object         | hello_world.zip                       |
      +----------------+---------------------------------------+

   .. end

#. Create a function and get the function ID, replace the
   ``runtime_id`` with the one in your deployment. Also, specify swift
   container and object name.

   .. code-block:: console

      openstack function create --name hello_world \
      --runtime $runtime_id \
      --entry hello_world.main \
      --container functions \
      --object hello_world.zip

      +-------------+----------------------------------------------------------------------------------------------+
      | Field       | Value                                                                                        |
      +-------------+----------------------------------------------------------------------------------------------+
      | id          | f1102bca-fbb4-4baf-874d-ed33bf8251f7                                                         |
      | name        | hello_world                                                                                  |
      | description | None                                                                                         |
      | count       | 0                                                                                            |
      | code        | {u'source': u'swift', u'swift': {u'object': u'hello_world.zip', u'container': u'functions'}} |
      | runtime_id  | 0d8bcf73-910b-4fec-86b1-38ace8bd0766                                                         |
      | entry       | hello_world.main                                                                             |
      | project_id  | 6ae7142bff0542d8a8f3859ffa184236                                                             |
      | created_at  | 2018-07-18 17:46:29.974506                                                                   |
      | updated_at  | None                                                                                         |
      | cpu         | 100                                                                                          |
      | memory_size | 33554432                                                                                     |
      +-------------+----------------------------------------------------------------------------------------------+

   .. end

#. Invoke the function by specifying function_id

   .. code-block:: console

      function_id=f1102bca-fbb4-4baf-874d-ed33bf8251f7
      openstack function execution create $function_id

      +------------------+-----------------------------------------------+
      | Field            | Value                                         |
      +------------------+-----------------------------------------------+
      | id               | 3451393d-60c6-4172-bbdf-c681929fae07          |
      | function_id      | f1102bca-fbb4-4baf-874d-ed33bf8251f7          |
      | function_version | 0                                             |
      | description      | None                                          |
      | input            | None                                          |
      | result           | {"duration": 0.031, "output": "Hello, World"} |
      | status           | success                                       |
      | sync             | True                                          |
      | project_id       | 6ae7142bff0542d8a8f3859ffa184236              |
      | created_at       | 2018-07-18 17:49:46                           |
      | updated_at       | 2018-07-18 17:49:48                           |
      +------------------+-----------------------------------------------+

   .. end

   It is very easy and simple to use Qinling with swift. We have successfully created and
   invoked a function using OpenStack Swift.

Create image(docker) type function
----------------------------------

With the help of Docker Hub you would be able to create image type functions in
Qinling. As a prerequisite, you need to have a Docker Hub account. In the
following instructions replace ``DOCKER_USER`` with your own docker hub
username.

#. In this tutorial we would be create docker image with latest Python3
   installed. We will create a python script which would be included in the image.
   Finally we create a Dockerfile to build the image.

   .. code-block:: console

      mkdir ~/qinling_test
      cd ~/qinling_test
      cat <<EOF > ~/qinling_test/hello.py
      import sys
      import time

      def main():
          print('Hello', sys.argv[1])
          time.sleep(3)

      if __name__ == '__main__':
          main()
      EOF

      cat <<EOF > ~/qinling_test/Dockerfile
      FROM python:3.7.0-alpine3.7
      COPY . /qinling_test
      WORKDIR /qinling_test
      ENTRYPOINT [ "python", "./hello.py" ]
      CMD ["Qinling"]
      EOF

   .. end

#. You need first run docker login to authenticate, build the image and push
   to Docker Hub.

   .. code-block:: console

      docker login
      docker build -t DOCKER_USER/qinling_test .
      docker push DOCKER_USER/qinlng_test

   .. end

#. Create an image type function by providing the docker image name.

   .. code-block:: console

      $ openstack function create --name docker_test --image DOCKER_USER/qinling_test
      +-------------+--------------------------------------------------------------+
      | Field       | Value                                                        |
      +-------------+--------------------------------------------------------------+
      | id          | 6fa6932d-ee43-41d4-891c-77a96b52c697                         |
      | name        | docker_test                                                  |
      | description | None                                                         |
      | count       | 0                                                            |
      | code        | {u'source': u'image', u'image': u'DOCKER_USER/qinling_test'} |
      | runtime_id  | None                                                         |
      | entry       | None                                                         |
      | project_id  | 6ae7142bff0542d8a8f3859ffa184236                             |
      | created_at  | 2018-08-05 00:37:07.336918                                   |
      | updated_at  | None                                                         |
      | cpu         | 100                                                          |
      | memory_size | 33554432                                                     |
      +-------------+--------------------------------------------------------------+

   .. end

#. Invoke the function by specifying the function name or ID.

   .. code-block:: console

      $ openstack function execution create docker_test
      +------------------+--------------------------------------+
      | Field            | Value                                |
      +------------------+--------------------------------------+
      | id               | 8fe0e2e9-2133-4abb-8cd4-f2f14935cab4 |
      | function_id      | 6fa6932d-ee43-41d4-891c-77a96b52c697 |
      | function_version | 0                                    |
      | description      | None                                 |
      | input            | None                                 |
      | result           | {"duration": 3}                      |
      | status           | success                              |
      | sync             | True                                 |
      | project_id       | 6ae7142bff0542d8a8f3859ffa184236     |
      | created_at       | 2018-08-05 00:37:25                  |
      | updated_at       | 2018-08-05 00:37:29                  |
      +------------------+--------------------------------------+

   .. end

#. Check the execution log.

   .. code-block:: console

      $ openstack function execution log show 8fe0e2e9-2133-4abb-8cd4-f2f14935cab4
      Hello Qinling

   .. end

Config timeout for the function
-------------------------------

In the cloud, you need to pay for the cloud resources that are used to run your
Qinling function. To prevent your function from running indefinitely, you
specify a timeout. When the specified timeout is reached, Qinling terminates
execution of the function. We recommend you set this value based on your
expected execution time. The default is 5 seconds and you can set it up to 300
seconds.

.. note::

   This guide assumes you already have a Python2 or Python3 runtime available
   in the deployment

#. Create a Python function that simply sleeps for 10 seconds to simulate a
   long-running function.

   .. code-block:: console

      mkdir ~/qinling_test && cd ~/qinling_test
      cat <<EOF > test_sleep.py
      import time
      def main(seconds=10, **kwargs):
          time.sleep(seconds)
      EOF

   .. end

#. Create the Qinling function.

   .. code-block:: console

      $ openstack function create --runtime $runtime_id --entry test_sleep.main --file ~/qinling_test/test_sleep.py --name test_sleep
      +-------------+-------------------------------------------------------------------------+
      | Field       | Value                                                                   |
      +-------------+-------------------------------------------------------------------------+
      | id          | 6c2cb248-5065-4a0a-9b7a-06818693358c                                    |
      | name        | test_sleep                                                              |
      | description | None                                                                    |
      | count       | 0                                                                       |
      | code        | {u'source': u'package', u'md5sum': u'c0830d40dbef48b11af9e63a653799ac'} |
      | runtime_id  | ba429da0-b800-4f27-96ea-eb527bd68004                                    |
      | entry       | test_sleep.main                                                         |
      | project_id  | d256a42b9f8e4d66805d91655b36a318                                        |
      | created_at  | 2018-09-10 01:43:06.250137                                              |
      | updated_at  | None                                                                    |
      | cpu         | 100                                                                     |
      | memory_size | 33554432                                                                |
      | timeout     | 5                                                                       |
      +-------------+-------------------------------------------------------------------------+

   .. end

#. Invoke the function. You will see the execution is terminated after about 5
   seconds(the default timeout).

   .. code-block:: console

      $ openstack function execution create test_sleep
      +------------------+--------------------------------------------------------------+
      | Field            | Value                                                        |
      +------------------+--------------------------------------------------------------+
      | id               | e096f4b3-85a7-4356-93e9-5f583e802aa2                         |
      | function_id      | 6c2cb248-5065-4a0a-9b7a-06818693358c                         |
      | function_version | 0                                                            |
      | description      | None                                                         |
      | input            | None                                                         |
      | result           | {"duration": 5.097, "output": "Function execution timeout."} |
      | status           | failed                                                       |
      | sync             | True                                                         |
      | project_id       | d256a42b9f8e4d66805d91655b36a318                             |
      | created_at       | 2018-09-10 01:44:46                                          |
      | updated_at       | 2018-09-10 01:44:55                                          |
      +------------------+--------------------------------------------------------------+

   .. end

#. Update the function by setting a longer timeout value.

   .. code-block:: console

      $ openstack function update test_sleep --timeout 15
      +-------------+-------------------------------------------------------------------------+
      | Field       | Value                                                                   |
      +-------------+-------------------------------------------------------------------------+
      | id          | 6c2cb248-5065-4a0a-9b7a-06818693358c                                    |
      | name        | test_sleep                                                              |
      | description | None                                                                    |
      | count       | 1                                                                       |
      | code        | {u'source': u'package', u'md5sum': u'c0830d40dbef48b11af9e63a653799ac'} |
      | runtime_id  | ba429da0-b800-4f27-96ea-eb527bd68004                                    |
      | entry       | test_sleep.main                                                         |
      | project_id  | d256a42b9f8e4d66805d91655b36a318                                        |
      | created_at  | 2018-09-10 01:43:06                                                     |
      | updated_at  | 2018-09-10 02:01:38.510319                                              |
      | cpu         | 100                                                                     |
      | memory_size | 33554432                                                                |
      | timeout     | 15                                                                      |
      +-------------+-------------------------------------------------------------------------+

   .. end

#. Invoke the function again to verify the function is successfully executed.

   .. code-block:: console

      $ openstack function execution create test_sleep
      +------------------+--------------------------------------+
      | Field            | Value                                |
      +------------------+--------------------------------------+
      | id               | 6dd91e1d-df91-4e19-92b6-3bec474ee09a |
      | function_id      | 6c2cb248-5065-4a0a-9b7a-06818693358c |
      | function_version | 0                                    |
      | description      | None                                 |
      | input            | None                                 |
      | result           | {"duration": 10.143, "output": null} |
      | status           | success                              |
      | sync             | True                                 |
      | project_id       | d256a42b9f8e4d66805d91655b36a318     |
      | created_at       | 2018-09-10 02:03:56                  |
      | updated_at       | 2018-09-10 02:04:06                  |
      +------------------+--------------------------------------+

   .. end
