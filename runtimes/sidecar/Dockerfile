FROM alpine:3.7
MAINTAINER lingxian.kong@gmail.com

# We need to use qinling user to keep consistent with server.
USER root
RUN adduser -HDs /bin/sh qinling

RUN apk update && \
    apk add --no-cache linux-headers build-base python2 python2-dev py2-pip uwsgi-python uwsgi-http && \
    pip install --upgrade pip && \
    rm -r /root/.cache

COPY . /sidecar
WORKDIR /sidecar
RUN pip install --no-cache-dir -r requirements.txt && \
    mkdir -p /var/lock/qinling && \
    mkdir -p /var/qinling/packages && \
    chown -R qinling:qinling /sidecar /var/lock/qinling /var/qinling/packages

EXPOSE 9091

# uwsgi --plugin http,python --http :9091 --uid qinling --wsgi-file sidecar.py --callable app --master --processes 1 --threads 1
CMD ["/usr/sbin/uwsgi", "--plugin", "http,python", "--http", "127.0.0.1:9091", "--uid", "qinling", "--wsgi-file", "sidecar.py", "--callable", "app", "--master", "--processes", "1", "--threads", "1"]