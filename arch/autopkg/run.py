#!/usr/bin/env python

import grp
import json
import os
import pwd
import re
import shutil
import sqlite3
import subprocess
import tarfile
import urllib.request as reqs
import urllib.parse as urlparse
import setup
# I *HATE* relying on non-stlib, and I hate even MORE that this is JUST TO COMPARE VERSION STRINGS.
# WHY IS THIS FUNCTIONALITY NOT STDLIB YET.
try:
    from distutils.version import LooseVersion
    has_lv = True
except ImportError:
    has_lv = False

# The base API URL (https://wiki.archlinux.org/index.php/Aurweb_RPC_interface)
aur_base = 'https://aur.archlinux.org/rpc/?v=5&type=info&by=name'
# The length of the above. Important because of uri_limit.
base_len = len(aur_base)
# Maximum length of the URI.
uri_limit = 4443

class PkgMake(object):
    def __init__(self, db = '~/.optools/autopkg.sqlite3'):
        db = os.path.abspath(os.path.expanduser(db))
        if not os.path.isfile(db):
            setup.firstrun(db)
        self.conn = sqlite3.connect(db)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        self.cfg = setup.main(self.conn, self.cur)
        if self.cfg['sign']:
            _cmt_mode = self.conn.isolation_level  # autocommit
            self.conn.isolation_level = None
            self.fpr, self.gpg = setup.GPG(self.cur, homedir = self.cfg['gpg_homedir'], keyid = self.cfg['gpg_keyid'])
            self.conn.isolation_level = _cmt_mode
            # don't need this anymore; it should be duplicated or populated into self.fpr.
            del(self.cfg['gpg_keyid'])
            self.my_key = self.gpg.get_key(self.fpr, secret = True)
            self.gpg.signers = [self.my_key]
        else:
            self.fpr = self.gpg = self.my_key = None
            del(self.cfg['gpg_keyid'])
        self.pkgs = {}
        self._populatePkgs()

    def main(self):
        self.getPkg()
        self.buildPkg()
        return()

    def _chkver(self, pkgbase):
        new_ver = self.pkgs[pkgbase]['meta']['new_ver']
        old_ver = self.pkgs[pkgbase]['meta']['pkgver']
        is_diff = (new_ver != old_ver)  # A super-stupid fallback
        if is_diff:
            if has_lv:
                is_diff = LooseVersion(new_ver) > LooseVersion(old_ver)
            else:
                # like, 90% of the time, this would work.
                new_tuple = tuple(map(int, (re.split('\.|-', new_ver))))
                old_tuple = tuple(map(int, (re.split('\.|-', old_ver))))
                # But people at https://stackoverflow.com/a/11887825/733214 are very angry about it, hence the above.
                is_diff = new_tuple > old_tuple
        return(is_diff)

    def _populatePkgs(self):
        # These columns/keys are inferred by structure or unneeded. Applies to both DB and AUR API.
        _notrack = ('pkgbase', 'pkgname', 'active', 'id', 'packagebaseid', 'numvotes', 'popularity', 'outofdate',
                    'maintainer', 'firstsubmitted', 'lastmodified', 'depends', 'optdepends', 'conflicts', 'license',
                    'keywords')
        _attr_map = {'version': 'new_ver'}
        # These are tracked per-package; all others are pkgbase and applied to all split pkgs underneath.
        _pkg_specific = ('pkgdesc', 'arch', 'url', 'license', 'groups', 'depends', 'optdepends', 'provides',
                         'conflicts', 'replaces', 'backup', 'options', 'install', 'changelog')
        _aur_results = []
        _urls = []
        _params = {'arg[]': []}
        _tmp_params = {'arg[]': []}
        self.cur.execute("SELECT * FROM packages WHERE active = '1'")
        for row in self.cur.fetchall():
            pkgbase = (row['pkgbase'] if row['pkgbase'] else row['pkgname'])
            pkgnm = row['pkgname']
            if pkgbase not in self.pkgs:
                self.pkgs[pkgbase] = {'packages': {pkgnm: {}},
                                      'meta': {}}
            for k in dict(row):
                if not k:
                    continue
                if k in _notrack:
                    continue
                if k in _pkg_specific:
                    self.pkgs[pkgbase]['packages'][pkgnm][k] = row[k]
                else:
                    if k not in self.pkgs[pkgbase]['meta']:
                        self.pkgs[pkgbase]['meta'][k] = row[k]
            # TODO: change this?
            pkgstr = urlparse.quote(pkgnm)  # We perform against a non-pkgbased name for the AUR search.
            _tmp_params['arg[]'].append(pkgstr)
            l = base_len + (len(urlparse.urlencode(_tmp_params, doseq = True)) + 1)
            if l >= uri_limit:
                # We need to split into multiple URIs based on URI size because of:
                # https://wiki.archlinux.org/index.php/Aurweb_RPC_interface#Limitations
                _urls.append('&'.join((aur_base, urlparse.urlencode(_params, doseq = True))))
                _params = {'arg[]': []}
                _tmp_params = {'arg[]': []}
            _params['arg[]'].append(pkgstr)
        _urls.append('&'.join((aur_base, urlparse.urlencode(_params, doseq = True))))
        for url in _urls:
            with reqs.urlopen(url) as u:
                _aur_results.extend(json.loads(u.read().decode('utf-8'))['results'])
        for pkg in _aur_results:
            pkg = {k.lower(): v for (k, v) in pkg.items()}
            pkgnm = pkg['name']
            pkgbase = pkg['packagebase']
            for (k, v) in pkg.items():
                if k in _notrack:
                    continue
                if k in _attr_map:
                    k = _attr_map[k]
                if k in _pkg_specific:
                    self.pkgs[pkgbase]['packages'][pkgnm][k] = v
                else:
                    self.pkgs[pkgbase]['meta'][k] = v
            self.pkgs[pkgbase]['meta']['snapshot'] = 'https://aur.archlinux.org{0}'.format(pkg['urlpath'])
            self.pkgs[pkgbase]['meta']['filename'] = os.path.basename(pkg['urlpath'])
            self.pkgs[pkgbase]['meta']['build'] = self._chkver(pkgbase)
        return()

    def _drop_privs(self):
        # First get the list of groups to assign.
        # This *should* generate a list *exactly* like as if that user ran os.getgroups(),
        # with the addition of self.cfg['build_user']['gid'] (if it isn't included already).
        newgroups = list(sorted([g.gr_gid
                                 for g in grp.getgrall()
                                 if pwd.getpwuid(self.cfg['build_user']['uid'])
                                 in g.gr_mem]))
        if self.cfg['build_user']['gid'] not in newgroups:
            newgroups.append(self.cfg['build_user']['gid'])
            newgroups.sort()
        # This is the user's "primary group"
        user_gid = pwd.getpwuid(self.cfg['build_user']['uid']).pw_gid
        if user_gid not in newgroups:
            newgroups.append(user_gid)
        os.setgroups(newgroups)
        # If we used os.setgid and os.setuid, we would PERMANENTLY/IRREVOCABLY drop privs.
        # Being that that doesn't suit the meta of the rest of the script (chmodding, etc.) - probably not a good idea.
        os.setresgid(self.cfg['build_user']['gid'], self.cfg['build_user']['gid'], -1)
        os.setresuid(self.cfg['build_user']['uid'], self.cfg['build_user']['uid'], -1)
        # Default on most linux systems. reasonable enough for building? (equal to chmod 755/644)
        os.umask(0o0022)
        # TODO: we need a full env construction here, I think, as well. PATH, HOME, GNUPGHOME at the very least?
        return()

    def _restore_privs(self):
        os.setresuid(self.cfg['orig_user']['uid'], self.cfg['orig_user']['uid'], self.cfg['orig_user']['uid'])
        os.setresgid(self.cfg['orig_user']['gid'], self.cfg['orig_user']['gid'], self.cfg['orig_user']['gid'])
        os.setgroups(self.cfg['orig_user']['groups'])
        os.umask(self.cfg['orig_user']['umask'])
        # TODO: if we change the env, we need to change it back here. I capture it in self.cfg['orig_user']['env'].
        return()

    def getPkg(self):
        self._drop_privs()
        for pkgbase in self.pkgs:
            if not self.pkgs[pkgbase]['meta']['build']:
                continue
            _pkgre = re.compile('^(/?.*/)*({0})/?'.format(pkgbase))
            builddir = os.path.join(self.cfg['cache'], pkgbase)
            try:
                shutil.rmtree(builddir)
            except FileNotFoundError:
                # We *could* use ignore_errors or onerrors params, but we only want FileNotFoundError.
                pass
            os.makedirs(builddir, mode = self.cfg['chmod']['dirs'], exist_ok = True)
            tarball = os.path.join(builddir, self.pkgs[pkgbase]['meta']['filename'])
            with reqs.urlopen(self.pkgs[pkgbase]['meta']['snapshot']) as url:
                # We have to write out to disk first because the tarfile module HATES trying to perform seeks on
                # a tarfile stream. It HATES it.
                with open(tarball, 'wb') as f:
                    f.write(url.read())
            tarnames = {}
            with tarfile.open(tarball, mode = 'r:*') as tar:
                for i in tar.getmembers():
                    if any((i.isdir(), i.ischr(), i.isblk(), i.isfifo(), i.isdev())):
                        continue
                    if i.name.endswith('.gitignore'):
                        continue
                    # We want to strip leading dirs out.
                    tarnames[i.name] = _pkgre.sub('', i.name)
                    # Small bugfix.
                    if tarnames[i.name] == '':
                        tarnames[i.name] = os.path.basename(i.name)
                    tarnames[i.name] = os.path.join(builddir, tarnames[i.name])
                for i in tar.getmembers():
                    if i.name in tarnames:
                        # GOLLY I WISH TARFILE WOULD LET US JUST CHANGE THE ARCNAME DURING EXTRACTION ON THE FLY.
                        with open(tarnames[i.name], 'wb') as f:
                            f.write(tar.extractfile(i.name).read())
            # No longer needed, so clean it up behind us.
            os.remove(tarball)
        self._restore_privs()
        return()

    def buildPkg(self):
        self._drop_privs()
        for pkgbase in self.pkgs:
            if not self.pkgs[pkgbase]['meta']['build']:
                continue
            builddir = os.path.join(self.cfg['cache'], pkgbase)
            os.chdir(builddir)
            # subprocess.run(['makepkg'])  # TODO: figure out gpg sig checking?
            subprocess.run(['makepkg', '--clean', '--force', '--skippgpcheck'])
        self._restore_privs()
        for pkgbase in self.pkgs:
            if not self.pkgs[pkgbase]['meta']['build']:
                continue
            builddir = os.path.join(self.cfg['cache'], pkgbase)
            # The i686 isn't even supported anymore, but let's keep this friendly for Archlinux32 folks.
            _pkgre = re.compile(('^({0})-{1}-'
                                     '(x86_64|i686|any)'
                                     '\.pkg\.tar\.xz$').format('|'.join(self.pkgs[pkgbase]['packages'].keys()),
                                                               self.pkgs[pkgbase]['meta']['new_ver']))
            fname = None
            # PROBABLY in the first root dir, and could be done with fnmatch, but...
            for root, dirs, files in os.walk(builddir):
                for f in files:
                    if _pkgre.search(f):
                        fname = os.path.join(root, f)
                        break
            if not fname:
                raise RuntimeError('Could not find proper package build filename for {0}'.format(pkgbase))
            destfile = os.path.join(self.cfg['dest'], os.path.basename(fname))
            os.rename(fname, destfile)
            # TODO: HERE IS WHERE WE SIGN THE PACKAGE?
            # We also need to update the package info in the DB.
            for p in self.pkgs[pkgbase]['packages']:
                self.cur.execute("UPDATE packages SET pkgver = ? WHERE pkgname = ?",
                                 (self.pkgs[pkgbase]['meta']['new_ver'], p))
            self.cfg['pkgpaths'].append(destfile)
            # No longer needed, so we can clear out the build directory.
            shutil.rmtree(builddir)
        os.chdir(self.cfg['dest'])
        dbfile = os.path.join(self.cfg['dest'], 'autopkg.db.tar.gz')  # TODO: Custom repo name?
        cmd = ['repo-add', '--nocolor', '--delta', dbfile]  # -s/--sign?
        cmd.extend(self.cfg['pkgpaths'])
        subprocess.run(cmd)
        for root, dirs, files in os.walk(self.cfg['dest']):
            for f in files:
                fpath = os.path.join(root, f)
                os.chmod(fpath, self.cfg['chmod']['files'])
                os.chown(fpath, self.cfg['chown']['uid'], self.cfg['chown']['gid'])
            for d in dirs:
                dpath = os.path.join(root, d)
                os.chmod(dpath, self.cfg['chmod']['dirs'])
                os.chown(dpath, self.cfg['chown']['uid'], self.cfg['chown']['gid'])
        return()

    def close(self):
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
        return()

def main():
    pm = PkgMake()
    pm.main()

if __name__ == '__main__':
    main()
