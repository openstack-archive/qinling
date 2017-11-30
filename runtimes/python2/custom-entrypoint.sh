#!/usr/bin/env bash
# This is expected to run as root for setting the ulimits

set -e

# ensure increased ulimits - for nofile - for the runtime containers
# the limit on the number of files that a single process can have open at a time
ulimit -n 1024

# ensure increased ulimits - for nproc - for the runtime containers
# the limit on the number of processes
ulimit -u 128

# ensure increased ulimits - for file size - for the runtime containers
# the limit on the total file size that a single process can create, 30M
ulimit -f 61440

/sbin/setuser qinling python -u server.py
