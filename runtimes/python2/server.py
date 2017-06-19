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

import json
import logging
import sys
import time
import zipfile
import zipimport

from flask import abort
from flask import Flask
from flask import request
from flask import Response
import requests

app = Flask(__name__)
zip_file = ''
function_module = 'main'
function_method = 'main'


@app.route('/download', methods=['POST'])
def download():
    download_url = request.form['download_url']
    function_id = request.form['function_id']
    entry = request.form['entry']
    token = request.form.get('token')

    headers = {}
    if token:
        headers = {'X-Auth-Token': token}

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

    importer = zipimport.zipimporter(zip_file)
    module = importer.load_module(function_module)

    input = {}
    if request.form:
        # Refer to:
        # http://werkzeug.pocoo.org/docs/0.12/datastructures/#werkzeug.datastructures.MultiDict
        input = request.form.to_dict()

    app.logger.debug('Invoking function with input: %s' % input)

    start = time.time()
    try:
        func = getattr(module, function_method)
        result = func(**input)
    except Exception as e:
        result = str(e)

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
