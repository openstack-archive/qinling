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


# Codes are from https://www.craig-wood.com/nick/articles/pi-machin/

def arctan_euler(x, one):
    x_squared = x * x
    x_squared_plus_1 = x_squared + 1
    term = (x * one) // x_squared_plus_1
    total = term
    two_n = 2
    while True:
        divisor = (two_n + 1) * x_squared_plus_1
        term *= two_n
        term = term // divisor
        if term == 0:
            break
        total += term
        two_n += 2
    return total


def pi_machin(one):
    return 4 * (4 * arctan_euler(5, one) - arctan_euler(239, one))


def main(digit=50000, *args, **kwargs):
    return str(pi_machin(10**digit))[:15]
