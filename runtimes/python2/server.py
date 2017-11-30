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
from multiprocessing import Manager
from multiprocessing import Process
import os
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
auth_url = None
username = None
password = None
trust_id = None


@app.route('/download', methods=['POST'])
def download():
    params = request.get_json() or {}

    download_url = params.get('download_url')
    function_id = params.get('function_id')
    entry = params.get('entry')

    global auth_url
    global username
    global password
    global trust_id
    token = params.get('token')
    auth_url = params.get('auth_url')
    username = params.get('username')
    password = params.get('password')
    trust_id = params.get('trust_id')

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


def _print_trace():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    print(''.join(line for line in lines))


def _invoke_function(execution_id, zip_file, module_name, method, input,
                     return_dict):
    """Thie function is supposed to be running in a child process."""
    sys.path.insert(0, zip_file)
    sys.stdout = open("%s.out" % execution_id, "w", 0)

    print('Start execution: %s' % execution_id)

    try:
        module = importlib.import_module(module_name)
        func = getattr(module, method)
        return_dict['result'] = func(**input)
        return_dict['success'] = True
    except Exception as e:
        if isinstance(e, OSError) and 'Resource' in str(e):
            sys.exit(1)

        return_dict['result'] = str(e)
        return_dict['success'] = False

        _print_trace()
    finally:
        print('Finished execution: %s' % execution_id)


@app.route('/execute', methods=['POST'])
def execute():
    """Invoke function.

    Several things need to handle in this function:
    - Save the function log
    - Capture the function internal exception
    - Deal with process execution error (The process may be killed for some
      reason, e.g. unlimited memory allocation)
    - Deal with os error for process (e.g. Resource temporarily unavailable)
    """

    global zip_file
    global function_module
    global function_method
    global auth_url
    global username
    global password
    global trust_id

    params = request.get_json() or {}
    input = params.get('input') or {}
    execution_id = params['execution_id']

    app.logger.info(
        'Request received, execution_id:%s, input: %s, auth_url: %s, '
        'username: %s, trust_id: %s' %
        (execution_id, input, auth_url, username, trust_id)
    )

    # Provide an openstack session to user's function
    os_session = None
    if auth_url:
        auth = generic.Password(
            username=username,
            password=password,
            auth_url=auth_url,
            trust_id=trust_id,
            user_domain_name='Default'
        )
        os_session = session.Session(auth=auth, verify=False)

    input.update({'context': {'os_session': os_session}})

    manager = Manager()
    return_dict = manager.dict()
    return_dict['success'] = False
    start = time.time()

    # Run the function in a separate process to avoid messing up the log
    p = Process(
        target=_invoke_function,
        args=(execution_id, zip_file, function_module, function_method,
              input, return_dict)
    )
    p.start()
    p.join()

    duration = round(time.time() - start, 3)

    # Process was killed unexpectedly or finished with error.
    if p.exitcode != 0:
        output = "Function execution failed because of too much resource " \
                 "consumption."
        success = False
    else:
        output = return_dict.get('result')
        success = return_dict['success']

    # Execution log
    with open('%s.out' % execution_id) as f:
        logs = f.read()
    os.remove('%s.out' % execution_id)

    return Response(
        response=json.dumps(
            {
                'output': output,
                'duration': duration,
                'logs': logs,
                'success': success
            }
        ),
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

# Just for testing purpose
app.run(host='0.0.0.0', port='9090', threaded=True)
