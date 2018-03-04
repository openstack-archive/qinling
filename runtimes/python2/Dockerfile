FROM phusion/baseimage:0.9.22
MAINTAINER anlin.kong@gmail.com

# We need to use non-root user because root user is not affected by ulimit.
USER root
RUN useradd -Ms /bin/bash qinling

RUN apt-get update && \
    apt-get -y install python-dev python-setuptools libffi-dev libxslt1-dev libxml2-dev libyaml-dev libssl-dev python-pip && \
    pip install -U pip setuptools uwsgi

COPY . /app
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt && \
    mkdir -p /var/qinling/packages && \
    chown -R qinling:qinling /app /var/qinling/packages

# uwsgi --http :9090 --uid qinling --wsgi-file server.py --callable app --master --processes 5 --threads 1
CMD ["/usr/local/bin/uwsgi", "--http", ":9090", "--uid", "qinling", "--wsgi-file", "server.py", "--callable", "app", "--master", "--processes", "5", "--threads", "1"]
