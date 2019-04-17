#!/usr/bin/env python3

import argparse
import io
import os
import pprint
import re
import sys
import tarfile


# PREREQS:
# Mostly stdlib.
#
# IF:
# 1.) You want to sign or verify packages (-s/--sign and -v/--verify, respectively),
# 2.) You want to work with delta updates,
# THEN:
# 1.) You need to install the python GnuPG GPGME bindings (the "gpg" module; NOT the "gpgme" module). They're
#     distributed with the GPG source. They're also in PyPI (https://pypi.org/project/gpg/).
# 2.) You need to install the xdelta3 module (https://pypi.org/project/xdelta3/).

_delta_re = re.compile('(.*)-*-*_to*')


class RepoMaint(object):
    def __init__(self, **kwargs):
        # https://stackoverflow.com/a/2912884/733214
        user_params = kwargs
        # Define a set of defaults to update with kwargs since we
        # aren't explicitly defining params.
        self.args = {'color': True,
                     'db': './repo.db.tar.xz',
                     'key': None,
                     'pkgs': [],
                     'quiet': False,
                     'sign': False,
                     'verify': False}
        self.args.update(user_params)
        self.db_exts = {'db.tar': False,  # No compression
                        'db.tar.xz': 'xz',
                        'db.tar.gz': 'gz',
                        'db.tar.bz2': 'bz2',
                        # We explicitly check False vs. None.
                        # For None, we do a custom check and wrap it.
                        # In .Z's case, we use the lzw module. It's the only non-stdlib compression
                        # that Arch Linux repo DB files support.
                        'db.tar.Z': None}
        self.args['db'] = os.path.abspath(os.path.expanduser(self.args['db']))
        self.db = None
        _is_valid_repo_db = False
        if not _is_valid_repo_db:
            raise ValueError(('Repo DB {0} is not a valid DB type. '
                              'Must be one of {1}.').format(self.args['db'],
                                                            ', '.join(['*.{0}'.format(i) for i in self.db_exts])))
        self.repo_dir = os.path.dirname(self.args['db'])
        self.lockfile = '{0}.lck'.format(self.args['db'])
        os.makedirs(self.repo_dir, exist_ok = True)
        self.gpg = None
        self.sigkey = None
        if self.args['sign'] or self.args['verify']:
            # Set up GPG handler.
            self._initGPG()
        self._importDB()

    def _initGPG(self):
        import gpg
        self.gpg = gpg.Context()
        if self.args['sign']:
            _seckeys = [k for k in self.gpg.keylist(secret = True) if k.can_sign]
            if self.args['key']:
                for k in _seckeys:
                    if self.sigkey:
                        break
                    for s in k.subkeys:
                        if self.sigkey:
                            break
                        if s.can_sign:
                            if self.args['key'].lower() in (s.keyid.lower(),
                                                            s.fpr.lower()):
                                self.sigkey = k
                                self.gpg.signers = [k]
            else:
                # Grab the first key that can sign.
                if _seckeys:
                    self.sigkey = _seckeys[0]
                    self.gpg.signers = [_seckeys[0]]
                if not self.args['quiet']:
                    print('Key ID not specified; using {0} as the default'.format(self.sigkey.fpr))
            if not self.sigkey:
                raise RuntimeError('Private key ID not found, cannot sign, or no secret keys exist.')
        # TODO: confirm verifying works without a key
        return()

    def _LZWcompress(self, data):
        # Based largely on:
        # https://github.com/HugoPouliquen/lzw-tools/blob/master/utils/compression.py
        data_arr = []
        rawdata = io.BytesIO(data)
        for i in range(int(len(data) / 2)):
            data_arr.insert(i, rawdata.read(2))
        w = bytes()
        b_size = 256
        b = []
        compressed = io.BytesIO()
        for c in data_arr:
            c = c.to_bytes(2, 'big')
            wc = w + c
            if wc in b:
                w = wc
            else:
                b.insert(b_size, wc)
                compressed.write(b.index(wc).to_bytes(2, 'big'))
                b_size += 1
                w = c
        return(compressed.getvalue())

    def _LZWdecompress(self, data):
        # Based largely on:
        # https://github.com/HugoPouliquen/lzw-tools/blob/master/utils/decompression.py
        b_size = 256
        b = []
        out = io.BytesIO()
        for i in range(b_size):
            b.insert(i, i.to_bytes(2, 'big'))
        w = data.pop(0)
        out.write(w)
        i = 0
        for byte in data:
            x = int.from_bytes(byte, byteorder = 'big')
            if x < b_size:
                entry = b[x]
            elif x == b_size:
                entry = w + w
            else:
                raise ValueError('Bad uncompressed value for "{0}"'.format(byte))
            for y in entry:
                if i % 2 == 1:
                    out.write(y.to_bytes(1, byteorder = 'big'))
                i += 1
            b.insert(b_size, w + x)
            b_size += 1
            w = entry
        return(out.getvalue())

    def _importDB(self):
        # Get the compression type.
        for ct in self.db_exts:
            if self.args['db'].lower().endswith(ct):
                if self.db_exts[ct] == False:
                    if ct.endswith('.Z'):  # Currently the only custom one.
                        pass


    def add(self):
        # Fresh pkg set (in case the instance was re-used).
        self.pkgs = {}
        # First handle any wildcard
        for p in self.args['pkgs'][:]:
            if p.strip() == '*':
                for root, dirs, files in os.walk(self.repo_dir):
                    for f in files:
                        abspath = os.path.join(root, f)
                        if f.endswith('.pkg.tar.xz'):  # Recommended not to be changed per makepkg.conf
                            if abspath not in self.args['pkgs']:
                                self.args['pkgs'].append(abspath)
                        if self.args['delta']:
                            if f.endswith('.delta'):
                                if abspath not in self.args['pkgs']:
                                    self.args['pkgs'].append(abspath)
                self.args['pkgs'].remove(p)
        # Then de-dupe and convert to full path.
        self.args['pkgs'] = sorted(list(set([os.path.abspath(os.path.expanduser(d)) for d in self.args['pkgs']])))
        for p in self.args['pkgs']:
            pkgfnm = os.path.basename(p)
            if p.endswith('.delta'):
                pkgnm = _delta_re.sub('\g<1>', os.path.basename(pkgfnm))

        return()

    def remove(self):
        for p in self.args['pkgs']:
            pass
        return()


def hatch():
    import base64
    import lzma
    import random
    h = ((
          '/Td6WFoAAATm1rRGAgAhARwAAAAQz1jM4AB6AEtdABBok+MQCtEh'
          'BisubEtc2ebacaLGrSRAMmHrcwUr39J24q4iODdNz7wfQl9e6I3C'
          'ooyuOkptNISdo50CRdknGAU4JBBh+IQTkHwiAAAABW1d7drLmkUA'
          'AWd7/+DtzR+2830BAAAAAARZWg=='
         ).encode('utf-8'),
         (
          '/Td6WFoAAATm1rRGAgAhARwAAAAQz1jM4AHEALtdABBpE/AVEKFC'
          'fdT16ly2cCwT/MnXTY2D4r8nWgH6mLetLPn17nza3ZK+tSFU7d5j'
          'my91M8fvPGu9Tf0NYkWlRU7vJM8r2V3kK/Gs6/GS7tq2qIum/C/X'
          'sOnYUewVB2yMvlACqwp3gWJlmXSfwcpGiU662EmATS8kUgF+OdP+'
          'EATXhM/1bAn07wJbVWPoAL2SBmJBo2zL1tXQklbQu1J20eWfd1bD'
          'cgSBGqcU1/CdHnW6lcb6BmWKTg0p9IAAAEoEyN1gLkAMAAHXAcUD'
          'AACXcduyscRn+wIAAAAABFla'
         ).encode('utf-8'))
    h = lzma.decompress(base64.b64decode(h[random.randint(0, 1)]))
    return(h.decode('utf-8'))


def parseArgs():
    args = argparse.ArgumentParser(description = ('Python implementation of repo-add/repo-remove.'),
                                   epilog = ('See https://wiki.archlinux.org/index.php/Pacman/'
                                             'Tips_and_tricks#Custom_local_repository for more information.\n'
                                             'Each operation has sub-help (e.g. "... add -h")'),
                                   formatter_class = argparse.RawDescriptionHelpFormatter)
    operargs = args.add_subparsers(dest = 'oper',
                                   help = ('Operation to perform'))
    commonargs = argparse.ArgumentParser(add_help = False)
    commonargs.add_argument('db',
                            metavar = '</path/to/repository/repo.db.tar.xz>',
                            help = ('The path to the repository DB (required)'))
    commonargs.add_argument('pkgs',
                            nargs = '+',
                            metavar = '<package|delta>',
                            help = ('Package filepath (for adding)/name (for removing) or delta; '
                                    'can be specified multiple times (at least 1 required)'))
    commonargs.add_argument('--nocolor',
                            dest = 'color',
                            action = 'store_false',
                            help = ('If specified, turn off color in output (currently does nothing; '
                                    'output is currently not colorized)'))
    commonargs.add_argument('-q', '--quiet',
                            dest = 'quiet',
                            action = 'store_true',
                            help = ('Minimize output'))
    commonargs.add_argument('-s', '--sign',
                            dest = 'sign',
                            action = 'store_true',
                            help = ('If specified, sign database with GnuPG after update'))
    commonargs.add_argument('-k', '--key',
                            metavar = 'KEY_ID',
                            nargs = 1,
                            help = ('Use the specified GPG key to sign the database '
                                    '(only used if -s/--sign is active)'))
    commonargs.add_argument('-v', '--verify',
                            dest = 'verify',
                            action = 'store_true',
                            help = ('If specified, verify the database\'s signature before update'))
    addargs = operargs.add_parser('add',
                                  parents = [commonargs],
                                  help = ('Add package(s) to a repository'))
    remargs = operargs.add_parser('remove',
                                  parents = [commonargs],
                                  help = ('Remove package(s) from a repository'))
    addargs.add_argument('-d', '--delta',
                         dest = 'delta',
                         action = 'store_true',
                         help = ('If specified, generate and add package deltas for the update'))
    addargs.add_argument('-n', '--new',
                         dest = 'new_only',
                         action = 'store_true',
                         help = ('If specified, only add packages that are not already in the database'))
    addargs.add_argument('-R', '--remove',
                         dest = 'remove_old',
                         action = 'store_true',
                         help = ('If specified, remove old packages from disk after updating the database'))
    # Removal args have no add'l arguments, just the common ones.
    return(args)

def main():
    if (len(sys.argv) == 2) and (sys.argv[1] == 'elephant'):
        print(hatch())
        return()
    else:
        rawargs = parseArgs()
        args = rawargs.parse_args()
        if not args.oper:
            rawargs.print_help()
            exit()
        rm = RepoMaint(**vars(args))
        if args.oper == 'add':
            rm.add()
        elif args.oper == 'remove':
            rm.remove()
    return()

if __name__ == '__main__':
    main()
