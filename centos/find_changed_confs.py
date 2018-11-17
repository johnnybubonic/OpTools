#!/usr/bin/env python

# Supports CentOS 6.9 and up, untested on lower versions.
# Definitely probably won't work on 5.x since they use MD5(?), and 6.5? and up
# use SHA256.

import argparse
import copy
import datetime
import hashlib
import os
import re
from sys import version_info as py_ver
try:
    import rpm
except ImportError:
    exit('This script only runs on RHEL/CentOS/other RPM-based distros.')

# Thanks, dude!
# https://blog.fpmurphy.com/2011/08/programmatically-retrieve-rpm-package-details.html

class PkgChk(object):
    def __init__(self, dirpath, symlinks = True, pkgs = None):
        self.path = dirpath
        self.pkgs = pkgs
        self.symlinks = symlinks
        self.orig_pkgs = copy.deepcopy(pkgs)
        self.pkgfilemap = {}
        self.flatfiles = []
        self.flst = {}
        self.trns = rpm.TransactionSet()
        self.getFiles()
        self.getActualFiles()

    def getFiles(self):
        if not self.pkgs:
            for p in self.trns.dbMatch():
                self.pkgs.append(p['name'])
        for p in self.pkgs:
            for pkg in self.trns.dbMatch('name', p):
                # Get the canonical package name
                _pkgnm = pkg.sprintf('%{NAME}')
                self.pkgfilemap[_pkgnm] = {}
                # Get the list of file(s) and their MD5 hash(es)
                for f in pkg.fiFromHeader():
                    if not f[0].startswith(self.path):
                        continue
                    if f[12] == '0' * 64:
                        _hash = None
                    else:
                        _hash = f[12]
                    self.pkgfilemap[_pkgnm][f[0]] = {'hash': _hash,
                                                     'date': f[3],
                                                     'size': f[1]}
                    self.flatfiles.append(f[0])
        return()

    def getActualFiles(self):
        print('Getting a list of local files and their hashes.')
        print('Please wait...\n')
        for root, dirs, files in os.walk(self.path):
            for f in files:
                _fpath = os.path.join(root, f)
                _stat = os.stat(_fpath)
                if _fpath in self.flatfiles:
                    _hash = hashlib.sha256()
                    with open(_fpath, 'rb') as r:
                        for chunk in iter(lambda: r.read(4096), b''):
                            _hash.update(chunk)
                    self.flst[_fpath] = {'hash': str(_hash.hexdigest()),
                                         'date': int(_stat.st_mtime),
                                         'size': _stat.st_size}
                else:
                    # It's not even in the package, so don't waste time
                    # with generating hashes or anything else.
                    self.flst[_fpath] = {'hash': None}
        return()

    def compareFiles(self):
        for f in self.flst.keys():
            if f not in self.flatfiles:
                if not self.orig_pkgs:
                    print(('{0} is not installed by any package.').format(f))
                else:
                    print(('{0} is not installed by package(s) ' +
                           'specified.').format(f))
            else:
                for p in self.pkgs:
                    if f not in self.pkgfilemap[p].keys():
                        continue
                    if (f in self.flst.keys() and
                            (self.flst[f]['hash'] !=
                             self.pkgfilemap[p][f]['hash'])):
                        if not self.symlinks:
                            if ((not self.pkgfilemap[p][f]['hash'])
                                or re.search('^0+$',
                                             self.pkgfilemap[p][f]['hash'])):
                                continue
                        r_time = datetime.datetime.fromtimestamp(
                                                self.pkgfilemap[p][f]['date'])
                        r_hash = self.pkgfilemap[p][f]['hash']
                        r_size = self.pkgfilemap[p][f]['size']
                        l_time = datetime.datetime.fromtimestamp(
                                                        self.flst[f]['date'])
                        l_hash = self.flst[f]['hash']
                        l_size = self.flst[f]['size']
                        r_str = ('\n{0} differs per {1}:\n' +
                                 '\tRPM:\n' +
                                 '\t\tSHA256: {2}\n' +
                                 '\t\tBYTES:  {3}\n' +
                                 '\t\tDATE:   {4}').format(f, p,
                                                           r_hash,
                                                           r_size,
                                                           r_time)
                        l_str = ('\tLOCAL:\n' +
                                 '\t\tSHA256: {0}\n' +
                                 '\t\tBYTES:  {1}\n' +
                                 '\t\tDATE:   {2}').format(l_hash,
                                                           l_size,
                                                           l_time)
                        print(r_str)
                        print(l_str)
        # Now we print missing files
        for f in sorted(list(set(self.flatfiles))):
            if not os.path.exists(f):
                print('{0} was deleted from the filesystem.'.format(f))
        return()

def parseArgs():
    def dirchk(path):
        p = os.path.abspath(path)
        if not os.path.isdir(p):
            raise argparse.ArgumentTypeError(('{0} is not a valid ' +
                                              'directory').format(path))
        return(p)
    args = argparse.ArgumentParser(description = ('Get a list of config ' +
                                                  'files that have changed ' +
                                                  'from the package\'s ' +
                                                  'defaults'))
    args.add_argument('-l', '--ignore-symlinks',
                      dest = 'symlinks',
                      action = 'store_false',
                      help = ('If specified, don\'t track files that are ' +
                              'symlinks in the RPM'))
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
    args.add_argument('dirpath',
                      type = dirchk,
                      metavar = 'path/to/directory',
                      help = ('The path to the directory containing the ' +
                              'configuration files to check against (e.g. ' +
                              '"/etc/ssh")'))
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    p = PkgChk(**args)
    p.compareFiles()

if __name__ == '__main__':
    main()
