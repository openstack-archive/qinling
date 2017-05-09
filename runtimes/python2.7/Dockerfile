FROM alpine:3.5

RUN apk update
RUN apk add --no-cache python2 python2-dev build-base py2-pip
RUN pip install --upgrade pip
RUN rm -r /root/.cache

COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt

ENTRYPOINT ["python"]
CMD ["server.py"]
