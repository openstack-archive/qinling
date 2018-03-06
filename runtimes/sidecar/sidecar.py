# Copyright 2018 Catalyst IT Limited
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

import os

from flask import Flask
from flask import make_response
from flask import request
from oslo_concurrency import lockutils
import requests

app = Flask(__name__)

DOWNLOAD_ERROR = "Failed to download function package from %s, error: %s"


@lockutils.synchronized('download_function', external=True,
                        lock_path='/var/lock/qinling')
def _download_package(url, zip_file, token=None):
    """Download package as needed.

    Return None if successful otherwise a Flask.Response object.
    """
    if os.path.isfile(zip_file):
        return None

    print('Downloading function, download_url:%s' % url)

    headers = {}
    if token:
        headers = {'X-Auth-Token': token}

    try:
        r = requests.get(url, headers=headers, stream=True, timeout=5,
                         verify=False)
        if r.status_code != 200:
            return make_response(DOWNLOAD_ERROR % (url, r.content), 500)

        with open(zip_file, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=65535):
                fd.write(chunk)
    except Exception as e:
        return make_response(DOWNLOAD_ERROR % (url, str(e)), 500)

    print('Downloaded function package to %s' % zip_file)


@app.route('/download', methods=['POST'])
def download():
    """Download function package to a shared folder.

    The parameters 'download_url' and 'function_id' need to be specified
    explicitly. It's guaranteed in the server side.
    """
    params = request.get_json()
    zip_file = '/var/qinling/packages/%s.zip' % params['function_id']

    resp = _download_package(
        params['download_url'],
        zip_file,
        params.get('token')
    )

    return resp if resp else 'downloaded'
