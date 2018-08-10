#!/usr/bin/env bash
# This is expected to run as root.

uwsgi --http :9090 --uid qinling --wsgi-file server.py --callable app --master --processes 5 --threads 1 &

uwsgi --http 127.0.0.1:9092 --uid root --wsgi-file cglimit.py --callable app --master --processes 1 --threads 1
