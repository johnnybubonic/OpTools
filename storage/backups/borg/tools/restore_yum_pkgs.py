#!/usr/bin/env python

import argparse  # yum install python-argparse on CentOS/RHEL 6.x
import os
import re
import subprocess
import sys
import warnings
##
# The yum API is *suuuper* cantankerous and kind of broken, even.
# Patches welcome, but for now we just use subprocess.
import yum
from lxml import etree  # yum install python-lxml


# Detect RH version.
ver_re =re.compile('^(centos.*|red\s?hat.*) ([0-9\.]+) .*$', re.IGNORECASE)
# distro module isn't stdlib, and platform.linux_distribution() (AND platform.distro()) are both deprecated in 3.7.
# So we get hacky.
with open('/etc/redhat-release', 'r') as f:
    rawver = f.read()
distver = [int(i) for i in ver_re.sub('\g<2>', rawver.strip()).split('.')]
distname = re.sub('(Linux )?release', '', ver_re.sub('\g<1>', rawver.strip()), re.IGNORECASE).strip()
# Regex pattern to get the repo name. We compile it just to speed up the execution.
repo_re = re.compile('^@')
# Python version
pyver = sys.hexversion
py3 = 0x30000f0  # TODO: check the version incompats

if pyver < py3:
    import copy


class Reinstaller(object):
    def __init__(self, pkglist_path, latest = True):
        self.latest = latest
        pkglist_file = os.path.abspath(os.path.expanduser(pkglist_path))
        with open(pkglist_file, 'rb') as f:
            self.pkgs = etree.fromstring(f.read())
        if not self.latest:
            # Make sure the versions match, otherwise Bad Things(TM) can occur.
            if not all(((distname == self.pkgs.attrib['distro']),
                        ('.'.join([str(i) for i in distver]) == self.pkgs.attrib['version']))):
                err = ('This package set was created on {0} {1}. '
                       'The current running OS is {2} {3} and you have set latest = False/None. '
                       'THIS IS A VERY BAD IDEA.').format(self.pkgs.attrib['distro'],
                                                          self.pkgs.attrib['version'],
                                                          distname,
                                                          '.'.join([str(i) for i in distver]))
                raise RuntimeError(err)
        # Make it run silently.
        self.yb = yum.YumBase()
        self.yb.preconf.quiet = 1
        self.yb.preconf.debuglevel = 0
        self.yb.preconf.errorlevel = 0
        self.yb.preconf.assumeyes = 1
        self.yb.preconf.rpmverbosity = 'error'

    def iterPkgs(self):
        for repo in self.pkgs.findall('repo'):
            # Base install packages ("anaconda") don't play nicely with this. They should be expected to
            # already be installed anyways, and self.latest is irrelevant - downgrading these can cause
            # *major* issues.
            # And "installed" repo are packages installed manually from RPM.
            if self.latest:
                if repo.attrib['name'].lower() in ('anaconda', 'installed'):
                    continue
            reponm = repo.attrib['desc']
            # This is only needed for the subprocess workaround.
            cmd = ['yum', '-q', '-y',
                   # '--disablerepo=*',
                   '--enablerepo={0}'.format(repo.attrib['name'])]
            pkgs = {'new': [],
                    'upgrade': [],
                    'downgrade': []}
            for pkg in repo.findall('package'):
                pkg_found = False
                is_installed = False
                if self.latest:
                    pkgnm = pkg.attrib['name']
                else:
                    pkgnm = pkg.attrib['NEVRA']
                pkglist = self.yb.doPackageLists(patterns = [pkgnm], showdups = True)
                if pkglist.updates:
                    for pkgobj in reversed(pkglist.updates):
                        if pkgobj.repo.name == reponm:
                            # Haven't gotten this working properly. Patches welcome.
                            # self.yb.install(po = pkgobj)
                            # self.yb.resolveDeps()
                            # self.yb.buildTransaction()
                            # self.yb.processTransaction()
                            if self.latest:
                                pkgs['upgrade'].append(pkgobj.name)
                            else:
                                if distver[0] >= 7:
                                    pkgs['upgrade'].append(pkgobj.nevra)
                                else:
                                    pkgs['upgrade'].append(pkgobj._ui_nevra())
                            pkg_found = True
                            is_installed = False
                            break
                if pkglist.installed and not pkg_found:
                    for pkgobj in reversed(pkglist.installed):
                        if pkgobj.repo.name == reponm:
                            if distver[0] >= 7:
                                nevra = pkgobj.nevra
                            else:
                                nevra = pkgobj._ui_nevra()
                            warn = ('{0} from {1} is already installed; skipping').format(nevra,
                                                                                          repo.attrib['name'])
                            warnings.warn(warn)
                            pkg_found = True
                            is_installed = True
                if not all((is_installed, pkg_found)):
                    if pkglist.available:
                        for pkgobj in reversed(pkglist.available):
                            if pkgobj.repo.name == reponm:
                                # Haven't gotten this working properly. Patches welcome.
                                # self.yb.install(po = pkgobj)
                                # self.yb.resolveDeps()
                                # self.yb.buildTransaction()
                                # self.yb.processTransaction()
                                if self.latest:
                                    pkgs['new'].append(pkgobj.name)
                                else:
                                    if distver[0] >= 7:
                                        pkgs['new'].append(pkgobj.nevra)
                                    else:
                                        pkgs['new'].append(pkgobj._ui_nevra())
                                is_installed = False
                                pkg_found = True
                                break
                    if not self.latest:
                        if pkglist.old_available:
                            for pkgobj in reversed(pkglist.old_available):
                                if pkgobj.repo.name == reponm:
                                    # Haven't gotten this working properly. Patches welcome.
                                    # self.yb.install(po = pkgobj)
                                    # self.yb.resolveDeps()
                                    # self.yb.buildTransaction()
                                    # self.yb.processTransaction()
                                    if distver[0] >= 7:
                                        pkgs['downgrade'].append(pkgobj.nevra)
                                    else:
                                        pkgs['downgrade'].append(pkgobj._ui_nevra())
                                    pkg_found = True
                                    break
            # # This... seems to always fail. Patches welcome.
            # # self.yb.processTransaction()
            for k in pkgs:
                if not pkgs[k]:
                    continue
                if pyver < py3:
                    _cmd = copy.deepcopy(cmd)
                else:
                    _cmd = cmd.copy()
                if k == 'downgrade':
                    _cmd.append('downgrade')
                else:
                    if self.latest:
                        _cmd.append('install')
                    else:
                        if distver[0] >= 7:
                            _cmd.append('install-nevra')
                        else:
                            _cmd.append('install')
                _cmd.extend(pkgs[k])
                if pyver >= py3:
                    subprocess.run(_cmd)
                else:
                    subprocess.call(_cmd)
        return()


def parseArgs():
    args = argparse.ArgumentParser(description = ('Reinstall packages from a generated XML package list'))
    args.add_argument('-V', '--version',
                      dest = 'latest',
                      action = 'store_false',
                      help = ('If specified, (try to) install the same version as specified in the package list.'))
    args.add_argument('pkglist_path',
                      metavar = 'PKGLIST',
                      help = ('The path to the generated packages XML file.'))
    return(args)

def main():
    args = parseArgs().parse_args()
    dictargs = vars(args)
    r = Reinstaller(**dictargs)
    r.iterPkgs()
    return()

if __name__ == '__main__':
    main()