#!/usr/bin/env python3

import os

selfpath = os.path.abspath(os.path.expanduser(__file__))
print(selfpath)

logmodpath = os.path.abspath(os.path.join(selfpath, '..', '..', '..', 'lib', 'python'))
print(logmodpath)
