FROM phusion/baseimage:0.9.22
MAINTAINER anlin.kong@gmail.com

# We need to use non-root user to execute functions and root user to set resource limits.
USER root
RUN useradd -Ms /bin/bash qinling

RUN apt-get update && \
    apt-get -y install python3-dev python3-setuptools libffi-dev libxslt1-dev libxml2-dev libyaml-dev libssl-dev python3-pip && \
    pip3 install -U pip setuptools uwsgi

COPY . /app
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt && \
    chmod 0750 custom-entrypoint.sh && \
    mkdir /qinling_cgroup && \
    mkdir -p /var/lock/qinling && \
    mkdir -p /var/qinling/packages && \
    chown -R qinling:qinling /app /var/qinling/packages

CMD ["/bin/bash", "custom-entrypoint.sh"]
