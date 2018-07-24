# Copyright 2018 AWCloud Software Co., Ltd
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

import hashlib
import requests


def main(url='https://docs.openstack.org/qinling/latest/', timeout=10,
         *args, **kwargs):
    # This function simply returns a sha256 hash of a webpage.
    # We use this to verify function pods have access the outside world.
    response = requests.get(url, timeout=timeout)
    return hashlib.sha256(response.text.encode('utf-8')).hexdigest()
