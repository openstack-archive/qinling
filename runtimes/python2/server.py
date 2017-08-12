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
import os
import sys
import time
import traceback
import zipfile

from flask import abort
from flask import Flask
from flask import request
from flask import Response
import requests

app = Flask(__name__)
zip_file = ''
function_module = 'main'
function_method = 'main'


# By default sys.stdout is usually line buffered for tty devices and fully
# buffered for other files. We need to change it to unbuffered to get execution
# log properly.
unbuffered = os.fdopen(sys.stdout.fileno(), 'w', 0)
sys.stdout = unbuffered


@app.route('/download', methods=['POST'])
def download():
    params = request.get_json() or {}
    download_url = params.get('download_url')
    function_id = params.get('function_id')
    entry = params.get('entry')
    token = params.get('token')

    headers = {}
    if token:
        headers = {'X-Auth-Token': token}

    global zip_file
    zip_file = '%s.zip' % function_id

    app.logger.info(
        'Request received, download_url:%s, headers: %s, entry: %s' %
        (download_url, headers, entry)
    )

    # Get function code package from Qinling service.
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

    params = request.get_json() or {}
    input = params.get('input') or {}
    execution_id = params['execution_id']
    print('Start execution: %s' % execution_id)
    app.logger.debug('Invoking function with input: %s' % input)

    start = time.time()
    try:
        sys.path.insert(0, zip_file)
        module = importlib.import_module(function_module)
        func = getattr(module, function_method)
        result = func(**input)
    except Exception as e:
        result = str(e)

        # Print stacktrace
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        app.logger.debug(''.join(line for line in lines))
    finally:
        print('Finished execution: %s' % execution_id)

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
