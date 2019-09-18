#!/usr/bin/env python3

# TODO: make as flexible as the <rpms>:/bin/build.py (flesh out args), logging, etc.

import argparse
import datetime
import copy
import io
import os
import pathlib
import re
import shutil
import subprocess
import tarfile
import tempfile
import warnings
##
import gpg
import requests
from lxml import etree


# TODO: track which versions are built so we don't need to consistently rebuild ALL packages
# TODO: should this be a configuration option?
aurbase = 'https://aur.archlinux.org'

_dflts = {'cfgfile': '~/.config/optools/arch/autorepo.xml'}


class Packager(object):
    def __init__(self, cfgfile = _dflts['cfgfile'], *args, **kwargs):
        user_params = kwargs
        self.args = copy.deepcopy(_dflts)
        self.args.update(user_params)
        self.origdir = os.path.abspath(os.path.expanduser(os.getcwd()))
        self.gpg = None
        self.args['destdir'] = os.path.abspath(os.path.expanduser(self.args['destdir']))
        if not self.args['pkgs']:
            self.args['pkgs'] = _dflts['pkgs']
        self._initSigner()

    def buildPkgs(self, auronly = None):
        for p in self.args['pkgs']:
            print(p)
            extract_dir = tempfile.mkdtemp(prefix = '.pkgbuilder.{0}-'.format(p))
            sub_extract_dir = os.path.join(extract_dir, p)
            has_pkg = False
            if not auronly:
                has_pkg = self._getLocal(p, extract_dir)
            if not has_pkg:
                has_pkg = self._getAUR(p, extract_dir)
            if not has_pkg:
                warnings.warn('Could not find package {0}; skipping...'.format(p))
                continue
            # We get a list of files to compare.
            prebuild_files = []
            postbuild_files = []
            for root, dirs, files in os.walk(sub_extract_dir):
                for f in files:
                    prebuild_files.append(os.path.join(root, f))
            os.chdir(os.path.join(extract_dir, p))
            # customizepkg-scripting in AUR
            try:
                custpkg_out = subprocess.run(['/usr/bin/customizepkg',
                                              '-m'],
                                             stdout = subprocess.PIPE,
                                             stderr = subprocess.PIPE)
            except FileNotFoundError:
                pass  # Not installed
            build_out = subprocess.run(['/usr/bin/multilib-build',
                                        '-c',
                                        '--',
                                        '--',
                                        '--skippgpcheck',
                                        '--syncdeps',
                                        '--noconfirm',
                                        '--log',
                                        '--holdver',
                                        '--skipinteg'],
                                       stdout = subprocess.PIPE,
                                       stderr = subprocess.PIPE)
            # with open('/tmp/build.log-{0}'.format(p), 'w') as f:
            #     f.write(build_out.stdout.decode('utf-8'))
            for root, dirs, files in os.walk(sub_extract_dir):
                for f in files:
                    fpath = os.path.join(root, f)
                    if fpath in prebuild_files:
                        continue
                    if fpath.endswith('.log'):
                        continue
                    postbuild_files.append(fpath)
            postbuild_files = [i for i in postbuild_files if i.endswith('.pkg.tar.xz')]
            if len(postbuild_files) != 1:
                warnings.warn('Could not reliably find a built package for {0}; skipping'.format(p))
            else:
                fdest = os.path.join(self.args['destdir'],
                                     os.path.basename(postbuild_files[0]))
                if os.path.isfile(fdest):
                    os.remove(fdest)
                shutil.move(postbuild_files[0], fdest)
                self._sign(fdest)
            os.chdir(self.origdir)
            shutil.rmtree(extract_dir)
        return()

    def _initSigner(self):
        self.gpg = gpg.Context()
        # Just grab the first private key until we flesh this out.
        for k in self.gpg.keylist(secret = True):
            if k.can_sign:
                self.gpg.signers = [k]
                break
        return()

    def _getAUR(self, pkgnm, extract_dir):
        dl_url = None
        pkg_srch = requests.get(os.path.join(self.args['aurbase'],
                                             'rpc'),
                                params = {
                                    'v': 5,
                                    'type': 'search',
                                    'by': 'name',
                                    'arg': pkgnm}).json()
        for pkg in pkg_srch['results']:
            dl_url = None
            if pkg['Name'] == pkgnm:
                dl_url = os.path.join(self.args['aurbase'], re.sub('^/+', '', pkg['URLPath']))
                # dl_file = os.path.basename(pkg['URLPath'])
                break
        if not dl_url:
            warnings.warn('Could not find a download path for {0}; skipping'.format(pkgnm))
            return(False)
        with requests.get(dl_url, stream = True) as url:
            with tarfile.open(mode = 'r|*', fileobj = io.BytesIO(url.content)) as tar:
                tar.extractall(extract_dir)
        return(True)

    def _getLocal(self, pkgnm, extract_dir):
        curfile = os.path.realpath(os.path.abspath(os.path.expanduser(__file__)))
        localpkg_dir = os.path.abspath(os.path.join(os.path.dirname(curfile),
                                                    '..',
                                                    'local_pkgs'))
        pkgbuild_dir = os.path.join(localpkg_dir,
                                    pkgnm)
        if not os.path.isdir(pkgbuild_dir):
            return(False)
        shutil.copytree(pkgbuild_dir, os.path.join(extract_dir, pkgnm))
        return(True)

    def _sign(self, pkgfile, passphrase = None):
        sigfile = '{0}.sig'.format(pkgfile)
        with open(pkgfile, 'rb') as pkg:
            with open(sigfile, 'wb') as sig:
                # We want ascii-armoured detached sigs
                sig.write(self.gpg.sign(pkg.read(), mode = gpg.constants.SIG_MODE_DETACH)[0])
        return()

    def createRepo(self):
        pkgfiles = []
        for root, dirs, files in os.walk(self.args['destdir']):
            for f in files:
                if f.endswith('.pkg.tar.xz'):
                    pkgfiles.append(os.path.join(root, f))
        repo_out = subprocess.run(['/usr/bin/repo-add',
                                   '-s',
                                   '-R',
                                   os.path.join(self.args['destdir'], '{0}.db.tar.xz'.format(self.args['reponame'])),
                                   *pkgfiles],
                                  stdout = subprocess.PIPE,
                                  stderr = subprocess.PIPE)
        return()


def parseArgs():
    args = argparse.ArgumentParser(description = 'Build Pacman packages and update a local repository')
    args.add_argument('-c', '--config',
                      dest = 'cfgfile',
                      default = _dflts['cfgfile'],
                      help = ('The path to the configuration file. Default: {0}').format(_dflts['cfgfile']))
    return(args)

def main():
    args = parseArgs().parse_args()
    varargs = vars(args)
    pkgr = Packager(**varargs)
    pkgr.buildPkgs(auronly = varargs['auronly'])
    pkgr.createRepo()
    return()

if __name__ == '__main__':
    main()
