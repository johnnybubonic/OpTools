#!/usr/bin/env python

# Supports CentOS 6.9 and up, untested on lower versions.
# Lets you get a list of files for a given package name(s) without installing
# any extra packages (such as yum-utils for repoquery).

# NOTE: If you're on CentOS 6.x, since it uses such an ancient version of python you need to either install
# python-argparse OR just resign to using it for all packages with none of the features.
try:
    import argparse
    has_argparse = True
except ImportError:
    has_argparse = False
import json
import os
import re
# For when CentOS/RHEL switch to python 3 by default (if EVER).
import sys
pyver = sys.version_info
try:
    import rpm
except ImportError:
    exit('This script only runs on the system-provided Python on RHEL/CentOS/other RPM-based distros.')

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
        self.files = {}
        for p in kwargs['pkgs']:
            if p not in self.files.keys():
                self.getFiles(p)
        if kwargs['rpm_files']:
            self.getLocalFiles(kwargs['rpm_files'])

    def getLocalFiles(self, rpm_files):
        # Needed because the rpm module can't handle arbitrary rpm files??? If it can, someone let me know.
        # According to http://rpm5.org/docs/api/classRpmhdr.html#_details I can.
        import yum
        for r in rpm_files:
            pkg = yum.YumLocalPackage(ts = self.trns,
                                      filename = r)
            _pkgnm = pkg.hdr.sprintf('%{NAME}')
            if _pkgnm in self.files:
                continue
            if self.verbose:
                self.files[_pkgnm] = {}
            else:
                self.files[_pkgnm] = []
            for f in pkg.hdr.fiFromHeader():
                _symlink = (True if re.search('^0+$', f[12]) else False)
                if self.verbose:
                    if _symlink:
                        if self.symlinks:
                            self.files[_pkgnm][f[0]] = '(symbolic link or directory)'
                        continue
                    self.files[_pkgnm][f[0]] = f[12]
                else:
                    # Skip if it is a symlink but they aren't enabled
                    if _symlink and not self.symlinks:
                        continue
                    else:
                        self.files[_pkgnm].append(f[0])
                    self.files[_pkgnm].sort()
        return()

    def getFiles(self, pkgnm):
        for pkg in self.trns.dbMatch('name', pkgnm):
            # The canonical package name
            _pkgnm = pkg.sprintf('%{NAME}')
            # Return just a list of files, or a dict of filepath:hash if verbose is enabled.
            if self.verbose:
                self.files[_pkgnm] = {}
            else:
                self.files[_pkgnm] = []
            for f in pkg.fiFromHeader():
                _symlink = (True if re.search('^0+$', f[12]) else False)
                if self.verbose:
                    if _symlink:
                        if self.symlinks:
                            self.files[_pkgnm][f[0]] = '(symbolic link)'
                        continue
                    self.files[_pkgnm][f[0]] = f[12]
                else:
                    # Skip if it is a symlink but they aren't enabled
                    if _symlink and not self.symlinks:
                        continue
                    else:
                        self.files[_pkgnm].append(f[0])
                    self.files[_pkgnm].sort()
        return()

def parseArgs():
    args = argparse.ArgumentParser(description = ('This script allows you get a list of files for a given package '
                                                  'name(s) without installing any extra packages (such as yum-utils '
                                                  'for repoquery). It is highly recommended to use at least one '
                                                  '-r/--rpm, -p/--package, or both.'))
    args.add_argument('-l', '--ignore-symlinks',
                      dest = 'symlinks',
                      action = 'store_false',
                      help = ('If specified, don\'t report files that are symlinks in the RPM'))
    args.add_argument('-v', '--verbose',
                      dest = 'verbose',
                      action = 'store_true',
                      help = ('If specified, include the hashes of the files'))
    args.add_argument('-r', '--rpm',
                      dest = 'rpm_files',
                      metavar = 'PATH/TO/RPM',
                      action = 'append',
                      default = [],
                      help = ('If specified, use this RPM file instead of the system\'s RPM database. Can be '
                              'specified multiple times'))
    args.add_argument('-p', '--package',
                      dest = 'pkgs',
                      #nargs = 1,
                      metavar = 'PKGNAME',
                      action = 'append',
                      default = [],
                      help = ('If specified, restrict the list of packages to check against to only this package. Can '
                              'be specified multiple times. HIGHLY RECOMMENDED'))
    return(args)

def main():
    if has_argparse:
        args = vars(parseArgs().parse_args())
        args['rpm_files'] = [os.path.abspath(os.path.expanduser(i)) for i in args['rpm_files']]
        if not any((args['rpm_files'], args['pkgs'])):
            prompt_str = ('You have not specified any package names.\nThis means we will get file lists for EVERY SINGLE '
                          'installed package.\nThis is a LOT of output and can take a few moments.\nIf this was a mistake, '
                          'you can hit ctrl-c now.\nOtherwise, hit the enter key to continue.\n')
            sys.stderr.write(prompt_str)
            if pyver.major >= 3:
                input()
            elif pyver.major == 2:
                raw_input()
            args['pkgs'] = all_pkgs()
    else:
        args = {'pkgs': all_pkgs(),
                'rpm_files': []}
    gf = FileGetter(**args)
    print(json.dumps(gf.files, indent = 4))
    return()

if __name__ == '__main__':
    main()
