FROM phusion/baseimage:0.9.22
MAINTAINER anlin.kong@gmail.com

USER root
RUN useradd -Ms /bin/bash qinling

RUN apt-get update && \
    apt-get -y install python-dev python-setuptools libffi-dev libxslt1-dev libxml2-dev libyaml-dev libssl-dev python-pip && \
    pip install -U pip setuptools

COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt && \
    chmod 0750 custom-entrypoint.sh && \
    chown -R qinling:qinling /app

CMD ["/bin/bash", "custom-entrypoint.sh"]
