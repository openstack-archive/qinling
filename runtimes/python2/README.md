# Qinling: Python Environment

This is the Python environment for Qinling.

It's a Docker image containing a Python 2.7 runtime, along with a
dynamic loader. A few common dependencies are included in the
requirements.txt file. End users need to provide their own dependencies
in their function packages through Qinling API or CLI.

## Rebuilding and pushing the image

You'll need access to a Docker registry to push the image, by default it's
docker hub. After modification, build a new image and upload to docker hub:

    docker build -t USER/python-runtime. && docker push USER/python-runtime


## Using the image in Qinling

After the image is ready in docker hub, create a runtime in Qinling:

    http POST http://127.0.0.1:7070/v1/runtimes name=python2.7 image=USER/python-runtime
