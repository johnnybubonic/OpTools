import datetime
import os
import re
import sys
##
from lxml import etree
try:
    # Note that currently, even on CentOS/RHEL 7, the yum module is only available for Python 2...
    # because reasons or something?
    # This may be re-done to allow for a third-party library in the case of python 3 invocation.
    import yum
    has_yum = True
except ImportError:
    # This will get *ugly*. You have been warned. It also uses more system resources and it's INCREDIBLY slow.
    # But it's safe.
    # Requires yum-utils to be installed.
    # It assumes a python 3 environment for the exact above reason.
    import subprocess
    has_yum = False

# See <optools>:/storage/backups/borg/tools/restore_yum_pkgs.py to use the XML file this generates.


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
                       output = '~/.cache/backup/misc/installed_pkgs.xml'):
        self.explicit_only = explicit_only
        self.include_deps = include_deps
        self.reasons = []
        if self.explicit_only:
            self.reasons.append('user')
        if self.include_deps:
            self.reasons.append('dep')
        self.output = os.path.abspath(os.path.expanduser(output))
        if has_yum:
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
        if has_yum:
            if not self.explicit_only:
                self.pkg_meta = self.yb.rpmdb.returnPackages()
            else:
                for pkg in self.yb.rpmdb.returnPackages():
                    reason = pkg.yumdb_info.get('reason')
                    if reason and reason.lower() in self.reasons:
                        self.pkg_meta.append(pkg)
        else:
            pass  # We do this in buildPkgInfo().
        return()

    def buildPkgInfo(self):
        if not has_yum:
            def repoQuery(nevra, fmtstr):
                cmd = ['/usr/bin/repoquery',
                       '--installed',
                       '--queryformat', fmtstr,
                       nevra]
                cmd_out = subprocess.run(cmd, stdout = subprocess.PIPE).stdout.decode('utf-8')
                return(cmd_out)
            _reason = '*'
            if self.reasons:
                if 'dep' not in self.reasons:
                    _reason = 'user'
            cmd = ['/usr/sbin/yumdb',
                   'search',
                   'reason',
                   _reason]
            rawpkgs = subprocess.run(cmd, stdout = subprocess.PIPE).stdout.decode('utf-8')
            reason_re = re.compile('^(\s+reason\s+=\s+.*|\s*)$')
            pkgs = []
            for line in rawpkgs.splitlines():
                if not reason_re.search(line):
                    pkgs.append(line.strip())
            for pkg_nevra in pkgs:
                reponame = repo_re.sub('', repoQuery(pkg_nevra, '%{ui_from_repo}')).strip()
                repo = self.pkgs.xpath('repo[@name="{0}"]'.format(reponame))
                if repo:
                    repo = repo[0]
                else:
                    # This is pretty error-prone. Fix/cleanup your systems.
                    repo = etree.Element('repo')
                    repo.attrib['name'] = reponame
                    rawrepo = subprocess.run(['/usr/bin/yum',
                                              '-v',
                                              'repolist',
                                              reponame],
                                             stdout = subprocess.PIPE).stdout.decode('utf-8')
                    urls = []
                    mirror = re.search('^Repo-mirrors\s*:', rawrepo, re.M)
                    repostatus = re.search('^Repo-status\s*:', rawrepo, re.M)
                    repourl = re.search('^Repo-baseurl\s*:', rawrepo, re.M)
                    repodesc = re.search('^Repo-name\s*:', rawrepo, re.M)
                    if mirror:
                        urls.append(mirror.group(0).split(':', 1)[1].strip())
                    if repourl:
                        urls.append(repourl.group(0).split(':', 1)[1].strip())
                    repo.attrib['urls'] = '>'.join(urls)  # https://stackoverflow.com/a/13500078
                    if repostatus:
                        repostatus = repostatus.group(0).split(':', 1)[1].strip().lower()
                        repo.attrib['enabled'] = ('true' if repostatus == 'enabled' else 'false')
                    else:
                        repo.attrib['enabled'] = 'false'
                    if repodesc:
                        repo.attrib['desc'] = repodesc.group(0).split(':', 1)[1].strip()
                    else:
                        repo.attrib['desc'] = '(metadata missing)'
                    self.pkgs.append(repo)
                pkgelem = etree.Element('package')
                pkginfo = {'NEVRA': pkg_nevra,
                           'desc': repoQuery(pkg_nevra, '%{summary}').strip()}
                # These are all values with no whitespace so we can easily combine into one call and then split them.
                (pkginfo['name'],
                 pkginfo['release'],
                 pkginfo['arch'],
                 pkginfo['version'],
                 pkginfo['built'],
                 pkginfo['installed'],
                 pkginfo['sizerpm'],
                 pkginfo['sizedisk']) = re.split('\t',
                                                 repoQuery(pkg_nevra,
                                                           ('%{name}\t'
                                                            '%{release}\t'
                                                            '%{arch}\t'
                                                            '%{ver}\t'  # version
                                                            '%{buildtime}\t'  # built
                                                            '%{installtime}\t'  # installed
                                                            '%{packagesize}\t'  # sizerpm
                                                            '%{installedsize}')  # sizedisk
                                                           ))
                for k in ('built', 'installed', 'sizerpm', 'sizedisk'):
                    pkginfo[k] = int(pkginfo[k])
                for k in ('built', 'installed'):
                    pkginfo[k] = datetime.datetime.fromtimestamp(pkginfo[k])
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
        else:
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
                        repo.attrib['enabled'] = ('true' if repoinfo in self.yb.repos.listEnabled() else 'false')
                        repo.attrib['desc'] = repoinfo.name
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
