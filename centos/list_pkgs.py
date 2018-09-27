#!/usr/bin/env python

# Supports CentOS 6.9 and up, untested on lower versions.
# Lets you get a list of files for a given package name(s) without installing
# any extra packages (such as yum-utils for repoquery).

import argparse
import json
import re
# For when CentOS/RHEL switch to python 3 by default (if EVER).
import sys
pyver = sys.version_info
try:
    import rpm
except ImportError:
    exit('This script only runs on RHEL/CentOS/other RPM-based distros.')

def all_pkgs():
    # Gets a list of all packages.
    pkgs = []
    trns = rpm.TransactionSet()
    for p in trns.dbMatch():
        pkgs.append(p['name'])
    pkgs = list(sorted(set(pkgs)))
    return(pkgs)

class FileGetter(object):
    def __init__(self, symlinks = True, verbose = False, *args, **kwargs):
        self.symlinks = symlinks
        self.verbose = verbose
        self.trns = rpm.TransactionSet()

    def getfiles(self, pkgnm):
        files = {}
        for pkg in self.trns.dbMatch('name', pkgnm):
            # The canonical package name
            _pkgnm = pkg.sprintf('%{NAME}')
            # Return just a list of files, or a dict of filepath:hash
            # if verbose is enabled.
            if self.verbose:
                files[_pkgnm] = {}
            else:
                files[_pkgnm] = []
            for f in pkg.fiFromHeader():
                _symlink = (True if re.search('^0+$', f[12]) else False)
                if self.verbose:
                    if _symlink:
                        if self.symlinks:
                            files[_pkgnm][f[0]] = '(symbolic link)'
                        continue
                    files[_pkgnm][f[0]] = f[12]
                else:
                    # Skip if it is a symlink but they aren't enabled
                    if _symlink and not self.symlinks:
                        continue
                    else:
                        files[_pkgnm].append(f[0])
                    files[_pkgnm].sort()
        return(files)

def parseArgs():
    args = argparse.ArgumentParser(description = (
                    'This script allows you get a list of files for a given '
                    'package name(s) without installing any extra packages '
                    '(such as yum-utils for repoquery).'))
    args.add_argument('-l', '--ignore-symlinks',
                      dest = 'symlinks',
                      action = 'store_false',
                      help = ('If specified, don\'t report files that are ' +
                              'symlinks in the RPM'))
    args.add_argument('-v', '--verbose',
                      dest = 'verbose',
                      action = 'store_true',
                      help = ('If specified, include the hashes of the files'))
    args.add_argument('-p', '--package',
                      dest = 'pkgs',
                      #nargs = 1,
                      metavar = 'PKGNAME',
                      action = 'append',
                      default = [],
                      help = ('If specified, restrict the list of ' +
                              'packages to check against to only this ' +
                              'package. Can be specified multiple times. ' +
                              'HIGHLY RECOMMENDED'))
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    if not args['pkgs']:
        prompt_str = (
            'You have not specified any package names.\nThis means we will '
            'get file lists for EVERY SINGLE installed package.\nThis is a '
            'LOT of output and can take a few moments.\nIf this was a '
            'mistake, you can hit ctrl-c now.\nOtherwise, hit the enter key '
            'to continue.\n')
        sys.stderr.write(prompt_str)
        if pyver.major >= 3:
            input()
        elif pyver.major == 2:
            raw_input()
        args['pkgs'] = all_pkgs()
    gf = FileGetter(**args)
    file_rslts = {}
    for p in args['pkgs']:
        if p not in file_rslts.keys():
            file_rslts[p] = gf.getfiles(p)
    print(json.dumps(file_rslts, indent = 4))
    return()

if __name__ == '__main__':
    main()
