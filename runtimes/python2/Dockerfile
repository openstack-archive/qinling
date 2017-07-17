FROM phusion/baseimage:0.9.22
MAINTAINER lingxian.kong@gmail.com

RUN apt-get update
RUN apt-get -y install python-dev python-setuptools libffi-dev libxslt1-dev libxml2-dev libyaml-dev libssl-dev python-pip
RUN pip install -U pip setuptools

COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "-u"]
CMD ["server.py"]
