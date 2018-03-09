# Copyright 2017 Catalyst IT Ltd
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

import resource


def main(number=1024, **kwargs):
    for name, desc in [
        ('RLIMIT_NOFILE', 'number of open files'),
    ]:
        limit_num = getattr(resource, name)
        soft, hard = resource.getrlimit(limit_num)
        print('Maximum %-25s (%-15s) : %20s %20s' % (desc, name, soft, hard))

    files = []

    try:
        for i in range(0, number):
            files.append(_create_file(i))
    finally:
        for f in files:
            f.close()


def _create_file(index):
    f = open('file_%s' % index, 'w')
    return f
