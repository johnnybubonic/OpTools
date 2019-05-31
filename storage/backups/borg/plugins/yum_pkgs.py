import datetime
import os
import re
import sys
##
from lxml import etree
import yum


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


class Backup(object):
    def __init__(self, explicit_only = True,
                       include_deps = False,
                       output = '~/.cache/backup/installed_pkgs.xml'):
        self.explicit_only = explicit_only
        self.include_deps = include_deps
        self.reasons = []
        if self.explicit_only:
            self.reasons.append('user')
        if self.include_deps:
            self.reasons.append('dep')
        self.output = os.path.abspath(os.path.expanduser(output))
        self.yb = yum.YumBase()
        # Make it run silently.
        self.yb.preconf.debuglevel = 0
        self.yb.preconf.errorlevel = 0
        self.pkg_meta = []
        # TODO: XSD?
        self.pkgs = etree.Element('packages')
        self.pkgs.attrib['distro'] = distname
        self.pkgs.attrib['version'] = '.'.join([str(i) for i in distver])
        self.pkglist = b''
        self.getPkgList()
        self.buildPkgInfo()
        self.write()

    def getPkgList(self):
        if not self.explicit_only:
            self.pkg_meta = self.yb.rpmdb.returnPackages()
        else:
            for pkg in self.yb.rpmdb.returnPackages():
                reason = pkg.yumdb_info.get('reason')
                if reason and reason.lower() in self.reasons:
                    self.pkg_meta.append(pkg)
        return()

    def buildPkgInfo(self):
        for pkg in self.pkg_meta:
            reponame = repo_re.sub('', pkg.ui_from_repo)
            repo = self.pkgs.xpath('repo[@name="{0}"]'.format(reponame))
            if repo:
                repo = repo[0]
            else:
                repo = etree.Element('repo')
                repo.attrib['name'] = reponame
                try:
                    repoinfo = self.yb.repos.repos[reponame]
                    repo.attrib['urls'] = '>'.join(repoinfo.urls)  # https://stackoverflow.com/a/13500078
                    repo.attrib['desc'] = repoinfo.name
                    repo.attrib['enabled'] = ('true' if repoinfo in self.yb.repos.listEnabled() else 'false')
                except KeyError:  # Repo is missing
                    repo.attrib['desc'] = '(metadata missing)'
                self.pkgs.append(repo)
            pkgelem = etree.Element('package')
            pkginfo = {'name': pkg.name,
                       'desc': pkg.summary,
                       'version': pkg.ver,
                       'release': pkg.release,
                       'arch': pkg.arch,
                       'built': datetime.datetime.fromtimestamp(pkg.buildtime),
                       'installed': datetime.datetime.fromtimestamp(pkg.installtime),
                       'sizerpm': pkg.packagesize,
                       'sizedisk': pkg.installedsize,
                       'NEVRA': pkg.nevra}
            for k, v in pkginfo.items():
                if pyver >= py3:
                    pkgelem.attrib[k] = str(v)
                else:
                    if isinstance(v, (int, long, datetime.datetime)):
                        pkgelem.attrib[k] = str(v).encode('utf-8')
                    elif isinstance(v, str):
                        pkgelem.attrib[k] = v.decode('utf-8')
                    else:
                        pkgelem.attrib[k] = v.encode('utf-8')
            repo.append(pkgelem)
        self.pkglist = etree.tostring(self.pkgs,
                                      pretty_print = True,
                                      xml_declaration = True,
                                      encoding = 'UTF-8')
        return()

    def write(self):
        outdir = os.path.dirname(self.output)
        if pyver >= py3:
            os.makedirs(outdir, exist_ok = True)
            os.chmod(outdir, mode = 0o0700)
        else:
            if not os.path.isdir(outdir):
                os.makedirs(outdir)
            os.chmod(outdir, 0o0700)
        with open(self.output, 'wb') as f:
            f.write(self.pkglist)
        return()
