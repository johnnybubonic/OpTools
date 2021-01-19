#!/usr/bin/env python3

import argparse
import hashlib
import os


_supported_hashes = hashlib.algorithms_available


class Hasher(object):
    def __init__(self, hashalgo = None):
        if hashalgo not in _supported_hashes:
            raise ValueError('hashalgo not in supported hash algorithm types')
        self.hash = hashlib.new(hashalgo)
        self.hashes = {}
