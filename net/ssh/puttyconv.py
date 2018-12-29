#!/usr/bin/env python3

## INCOMPLETE ##
# TODO

import argparse

def parseArgs():
    args = argparse.ArgumentParser(description = 'Convert private and public SSH keys between PuTTY/OpenSSH format')
    args.add_argument('-l', '--legacy',
                      dest = 'legacy_ssh',
                      action = 'store_true',
                      help = ('If specified, try to handle the OpenSSH key as the legacy format ("") rather than the '
                              'newer '
                              'more compact format ("")'))
    ktype = args.add_mutually_exclusive_group()
    ktype.add_argument('-s', '--ssh',
                       dest = 'ktype',
                       const = 'openssh',
                       help = ('Force the conversion to OpenSSH format'))
    ktype.add_argument('-p', '--putty',
                       dest = 'ktype',
                       const = 'putty',
                       help = ('Force the conversion to PuTTY format'))
