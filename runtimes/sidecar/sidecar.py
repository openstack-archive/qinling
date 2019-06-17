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

import logging
import os
import sys
import zipfile

from flask import Flask
from flask import make_response
from flask import request
from oslo_concurrency import lockutils
import requests

app = Flask(__name__)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
del app.logger.handlers[:]
app.logger.addHandler(ch)

DOWNLOAD_ERROR = "Failed to download function package from %s, error: %s"


def log(message, level="info"):
    global app
    log_func = getattr(app.logger, level)
    log_func(message)


@lockutils.synchronized('download_function', external=True,
                        lock_path='/var/lock/qinling')
def _download_package(url, zip_file, token=None, unzip=None):
    """Download package and unzip as needed.

    Return None if successful otherwise a Flask.Response object.
    """
    if os.path.isfile(zip_file):
        return None

    log("Start downloading function")

    headers = {}
    if token:
        headers = {'X-Auth-Token': token}

    try:
        r = requests.get(url, headers=headers, stream=True, timeout=30,
                         verify=False)
        if r.status_code != 200:
            return make_response(DOWNLOAD_ERROR % (url, r.content), 500)

        with open(zip_file, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=65535):
                fd.write(chunk)

        log("Downloaded function package to %s" % zip_file)

        if unzip:
            dest = zip_file.split('.')[0]
            with open(zip_file, 'rb') as f:
                zf = zipfile.ZipFile(f)
                zf.extractall(dest)
            log("Unzipped")
    except Exception as e:
        return make_response(DOWNLOAD_ERROR % (url, str(e)), 500)


@app.route('/download', methods=['POST'])
def download():
    """Download function package to a shared folder.

    The parameters 'download_url' and 'function_id' need to be specified
    explicitly. It's guaranteed on the server side.

    :param download_url: The URL for function package download. It's a Qinling
        function resource URL with 'download' enabled.
    :param function_id: Function ID.
    :param token: Optional. The token used for download.
    :param unzip: Optional. If unzip is needed after download.
    """
    params = request.get_json()
    zip_file = '/var/qinling/packages/%s.zip' % params['function_id']
    log("Function package download request received, params: %s" % params)

    resp = _download_package(
        params['download_url'],
        zip_file,
        token=params.get('token'),
        unzip=params.get('unzip', True)
    )

    return resp if resp else 'downloaded'
