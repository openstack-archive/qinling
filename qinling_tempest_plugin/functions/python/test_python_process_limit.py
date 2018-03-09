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

from multiprocessing import Process
import resource
import time


def main(number=10, **kwargs):
    soft, hard = resource.getrlimit(resource.RLIMIT_NPROC)
    print('(soft, hard): %20s %20s' % (soft, hard))

    # We set a small number inside the function to avoid being affected by
    # outside.
    resource.setrlimit(resource.RLIMIT_NPROC, (number, hard))

    processes = []
    for i in range(0, number+1):
        p = Process(
            target=_sleep,
            args=(i,)
        )
        p.start()
        processes.append(p)
    for p in processes:
        p.join()


def _sleep(index):
    time.sleep(10)
