# Copyright 2017 Catalyst IT Limited
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import importlib
import json
import logging
import sys
import time
import traceback
import zipfile

from flask import abort
from flask import Flask
from flask import request
from flask import Response
from keystoneauth1.identity import generic
from keystoneauth1 import session
import requests

app = Flask(__name__)
zip_file = ''
function_module = 'main'
function_method = 'main'
openstack_session = None


@app.route('/download', methods=['POST'])
def download():
    params = request.get_json() or {}
    download_url = params.get('download_url')
    function_id = params.get('function_id')
    entry = params.get('entry')
    token = params.get('token')
    auth_url = params.get('auth_url')

    headers = {}
    if token:
        headers = {'X-Auth-Token': token}

        # Get openstack session.
        global openstack_session
        auth = generic.Token(auth_url=auth_url, token=token)
        openstack_session = session.Session(auth=auth, verify=False)

    global zip_file
    zip_file = '%s.zip' % function_id

    app.logger.info(
        'Request received, download_url:%s, headers: %s, entry: %s' %
        (download_url, headers, entry)
    )

    r = requests.get(download_url, headers=headers, stream=True)
    with open(zip_file, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=65535):
            fd.write(chunk)

    if not zipfile.is_zipfile(zip_file):
        abort(500)
    app.logger.info('Code package downloaded to %s' % zip_file)

    global function_module
    global function_method
    function_module, function_method = tuple(entry.rsplit('.', 1))

    return 'success'


@app.route('/execute', methods=['POST'])
def execute():
    global zip_file
    global function_module
    global function_method
    global openstack_session

    context = {'os_session': openstack_session}
    input = request.get_json() or {}
    app.logger.debug('Invoking function with input: %s' % input)

    start = time.time()
    try:
        sys.path.insert(0, zip_file)
        module = importlib.import_module(function_module)
        func = getattr(module, function_method)
        result = func(context=context, **input)
    except Exception as e:
        result = str(e)

        # Print stacktrace
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        app.logger.debug(''.join(line for line in lines))

    duration = time.time() - start
    return Response(
        response=json.dumps({'output': result, 'duration': duration}),
        status=200,
        mimetype='application/json'
    )


def setup_logger(loglevel):
    global app
    root = logging.getLogger()
    root.setLevel(loglevel)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(loglevel)
    ch.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    )
    app.logger.addHandler(ch)


setup_logger(logging.DEBUG)
app.logger.info("Starting server")
app.run(host='0.0.0.0', port='9090')
