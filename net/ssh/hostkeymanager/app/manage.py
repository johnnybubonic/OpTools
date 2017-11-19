#!/usr/bin/env python3

import argparse
import sys
import os
# This is ugly as fuck. TODO: can we do this more cleanly?
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
import config

class DBmgr(object):
    def __init__(self, args = None):
        self.DB = config.DB
        self.args = args

    def keyChk(self):
        # Is it a pubkey file?
        if os.path.isfile(os.path.abspath(os.path.expanduser(self.args['key']))):
            with open(os.path.abspath(os.path.expanduser(self.args['key'])), 'r') as f:
                self.args['key'] = f.read()
        self.args['key'] = self.args['key'].strip()


    def add(self, key, host, role):
        pass

def argParse():
    args = argparse.ArgumentParser()
    args.add_argument('-k',
                      '--key',
                      dest = 'key',
                      default = None,
                      type = 'str',

    return(args)

def main():
    args -
    d = DBmgr(args)

if __name__ == '__main__':
    main()
