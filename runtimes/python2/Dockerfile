FROM phusion/baseimage:0.9.22
MAINTAINER anlin.kong@gmail.com

USER root
RUN useradd -Ms /bin/bash qinling

RUN apt-get update && \
    apt-get -y install python-dev python-setuptools libffi-dev libxslt1-dev libxml2-dev libyaml-dev libssl-dev python-pip && \
    pip install -U pip setuptools uwsgi

COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt && \
    chmod 0750 custom-entrypoint.sh && \
    mkdir -p /var/lock/qinling && \
    chown -R qinling:qinling /app /var/lock/qinling

# uwsgi --http :9090 --uid qinling --wsgi-file server.py --callable app --master --processes 5 --threads 1
CMD ["/usr/local/bin/uwsgi", "--http", ":9090", "--uid", "qinling", "--wsgi-file", "server.py", "--callable", "app", "--master", "--processes", "5", "--threads", "1"]
