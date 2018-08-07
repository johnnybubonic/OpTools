#!/usr/bin/env python3

import configparser
import copy
import datetime
import importlib
import os
import platform
import re
import socket
import subprocess
import sys

cfgfile = os.path.join(os.environ['HOME'],
                       '.config',
                       'optools',
                       'repoclone',
                       'centos.ini')

# Set up the logger.
_selfpath = os.path.abspath(os.path.realpath(os.path.expanduser(__file__)))
_logmodpath = os.path.abspath(os.path.join(_selfpath,
                                           '..', '..', '..',
                                           'lib',
                                           'python',
                                           'logger.py'))
log_spec = importlib.util.spec_from_file_location('logger', _logmodpath)
logger = importlib.util.module_from_spec(log_spec)
log_spec.loader.exec_module(logger)

_loglevel = 'warning'
#_loglevel = 'debug'

class cur_ver(object):
    def __init__(self):
        # TODO: .dist() is deprecated, as is linux_distribution.
        # switch to distro? https://pypi.org/project/distro
        _distname = platform.dist()[0]
        if not re.search('^CentOS( Linux)?$', _distname, re.IGNORECASE):
            raise ValueError(('You have specified "{cur_ver}" in your ' +
                              'config, but you are not running this script ' +
                              'on CentOS!'))
        _ver = platform.dist()[1].split('.')
        self.full = '.'.join(_ver)
        self.maj = int(_ver[0])
        self.min = int(_ver[1])
        self.rev = _ver[2]

    def __str__(self):
        return(self.full)

# Rsync options
opts = [
        '--recursive',  # recurse into directories
        '--times',  # preserve modification times
        '--links',  # copy symlinks as symlinks
        '--hard-links',  # preserve hard links
        '--quiet',  # suppress non-error messages
        '--delete-after',  # receiver deletes after transfer, not during
        '--delay-updates',  # put all updated files into place at end
        '--copy-links',  # transform symlink into referent file/dir
        '--safe-links',  # ignore symlinks that point outside the tree
        #'--max-delete',  # don't delete more than NUM files
        '--delete-excluded',  # also delete excluded files from dest dirs
       ]

dflts = {'DEFAULT': {'repo_name': '{name}',
                     'enabled': False,
                     'arches': ['i686', 'x86_64'],
                     'baseuri': ('mirror.centos.org/centos/{rel_ver}/' +
                                 '${repo_name}/{arch}'),
                     'destination': ('${mount}/centos/{rel_ver}/' +
                                     '${repo_name}/{arch}'),
                     'mount': '/mnt/repos',
                     'bwlimit': 0,
                     'lockfile': '/var/run/repo-sync_{name}.lck',
                     'logfile': '/var/log/repo/centos.log',
                     'releases': [6, 7],
                     'excludes': None},
         'base': {'repo_name': 'os',
                  'enabled': True},
         'updates': {'enabled': True},
         'extras': {'enabled': True},
         'centosplus': {'enabled': True},
         'epel': {'enabled': True,
                  'baseuri': ('dl.fedoraproject.org::fedora-{name}0/' +
                              '{rel_ver}/{arch}'),
                  'destination': '${mount}/centos/{name}/{rel_ver}/{arch}'},
         'ius': {'enabled': False,
                 'baseuri': ('dl.iuscommunity.org/{name}/stable/CentOS/' +
                             '{rel_ver}/{arch}')}}

class MirrorMgr(object):
    def __init__(self):
        self.cfg = configparser.ConfigParser(
                        interpolation = configparser.ExtendedInterpolation(),
                        defaults = dflts['DEFAULT'],
                        allow_no_value = True)
        self.strvars = {'cur_ver': None,
                        'name': None,
                        'arches': [],
                        'releases': [],
                        'cur_arch': platform.machine(),
                        'rel_ver': None,
                        'arch': None}
        if not os.path.isfile(cfgfile):
            self.gen_cfg()
        self.get_cfg()
        self.chk_cur_ver()
        self.parse_cfg()
        self.log = logger.log(os.path.abspath(os.path.expanduser(
                                               logfile = self.cfg['DEFAULT'])),
                              logname = 'optools.repoclone.centos',
                              loglvl = _loglevel)

    def get_cfg(self):
        with open(cfgfile, 'r') as f:
            self.cfg_in = f.read()
        return()

    def chk_cur_ver(self):
        for line in self.cfg_in.splitlines():
            _line = line
            # Strip out inline comments -- this is disabled by default(?).
            #_line = re.sub('\s*(#|;).*$', '', line)
            # Skip empty lines/comments.
            if re.search('^\s*((#|;).*)?$', line):
                continue
            # Check to see if cur_ver is referenced.
            if re.search('^.*{cur_ver}.*$', _line):
                self.strvars['cur_ver'] = cur_ver()
                break
        return()

    def gen_cfg(self):
        cfg = configparser.ConfigParser(
                        interpolation = configparser.ExtendedInterpolation(),
                        defaults = dflts['DEFAULT'],
                        allow_no_value = True)
        for i in dflts.keys():
            if i != 'DEFAULT':
                cfg[i] = copy.deepcopy(dflts[i])
        with open(cfgfile, 'w') as f:
            cfg.write(f)
        # And add the comment about how it's a stripped down default conf.
        with open(cfgfile, 'r+') as f:
            cfgdata = f.read()
            f.seek(0, 0)
            cmnt = ('# This is an autogenerated configuration file for ' +
                    'r00t^s\'s OpTools CentOS\n# mirror script.\n# You ' +
                    'should reference the fully commented version ' +
                    'distributed with the script,\n# "centos.dflts.ini".\n\n')
            f.write(cmnt + cfgdata)
        print(('A configuration file has been automatically generated for ' +
               'you at {0}. You should review and customize it, because it ' +
               'most likely will not work out of the box.').format(cfgfile))
        exit('Exiting to give you the chance to customize it...')
        return()

    def parse_cfg(self):
        self.cfg.read_string(self.cfg_in)
        return()

    def sync(self):
        for repo in self.cfg.sections():
            # Skip disabled repos.
            if not self.cfg.getboolean(repo, 'enabled'):
                continue
            self.repo = copy.deepcopy(dict(self.cfg[repo]))
            self.strvars['name'] = repo
            # This should be safe since the only thing that makes sense here is
            # {cur_arch}, which we populate in __init__().
            self.strvars['arches'] = [i.strip() for i in \
                                      self.repo['arches'].format(
                                                    **self.strvars).split(',')]
            self.strvars['releases'] = [i.strip() for i in \
                                        self.repo['releases'].format(
                                                    **self.strvars).split(',')]
            for arch in self.strvars['arches']:
                for rel_ver in self.strvars['releases']:
                    self._clear_tpl(repo, arch, rel_ver)
                    self._repo_chk(repo)
                    self._repo_sync(repo)
        return()

    def _clear_tpl(self, repo, arch, rel_ver):
        self.repo = copy.deepcopy(dict(self.cfg[repo]))
        self.strvars['name'] = repo
        # This should be safe since the only thing that makes sense here is
        # {cur_arch}, which we populate in __init__().
        self.strvars['arches'] = [i.strip() for i in \
                                  self.repo['arches'].format(
                                                **self.strvars).split(',')]
        self.strvars['releases'] = [i.strip() for i in \
                                    self.repo['releases'].format(
                                                **self.strvars).split(',')]
        self.strvars['arch'] = arch
        self.strvars['rel_ver'] = rel_ver
        self.strvars['name'] = repo
        self._repo_chk(repo)
        return()

    def _repo_sync(self, repo):
        # Reset the Rsync options
        self.opts = opts
        self.repo['bwlimit'] = float(self.repo['bwlimit'])
        if self.repo['bwlimit'] > 0.0:
            # limit socket I/O bandwidth
            self.opts.append('--bwlimit=' + str(self.repo['bwlimit']))
        paths = os.environ['PATH'].split(':')
        cmd = ['rsync']  # Set up a cmd list for subprocess
        cmd.extend(opts)  # The arguments for rsync
        # The path on the remote mirror
        _path = os.path.join('rsync://{0}'.format(self.repo['baseuri']), '.')
        cmd.append(_path)
        # The local destination
        cmd.append(os.path.join(self.repo['destination'], '.'))
        if os.path.isfile(self.repo['lockfile']):
            with open(self.repo['lockfile'], 'r') as f:
                existingpid = f.read().strip()
            if os.isatty(sys.stdin.fileno()):
                # Running from shell
                exit(('!! A repo synchronization seems to already be ' +
                      'running (PID: {0}). Quitting. !!').format(existingpid))
            else:
                exit()  # We're running in cron, shut the hell up.
        else:
            with open(self.repo['lockfile'], 'w') as f:
                f.write(str(os.getpid()))
        with open(self.repo['logfile'], 'a') as log:
            c = subprocess.run(cmd, stdout = log, stderr = subprocess.PIPE)
            now = int(datetime.datetime.utcnow().timestamp())
            with open(os.path.join(self.repo['destination'],
                                   'lastsync'), 'w') as f:
                f.write(str(now) + '\n')
            os.remove(self.repo['lockfile'])
            # Only report errors at the end of the run if we aren't running in
            # cron. Otherwise, log them.
            errors = c.stderr.decode('utf-8').splitlines()
            # CentOS 7 main doesn't have an i686.
            if self.strvars['rel_ver'] == 7:
                for e in errors[:]:
                    rgx = re.compile(('^rsync: change_dir.*/i[36]86(/|").*' +
                                      'failed:\s*No\s+such\s+file\s+or\s+' +
                                      'directory.*$'))
                    if rgx.search(e):
                        errors.remove(e)
            for e in errors[:]:
                if e.startswith(('rsync error: some files/attrs were not ' +
                                 'transferred (see previous errors)')):
                    errors.remove(e)
            if os.isatty(sys.stdin.fileno()) and errors:
                print('[{0}] We encountered some errors:'.format(repo))
                for e in errors:
                    if e.startswith('symlink has no referent: '):
                        print(('Broken upstream symlink: ' +
                               '{0}').format(e.split()[1].replace('"', '')))
                    else:
                        print(e)
            else:
                for e in errors:
                    log.write('{0}\n'.format(e))
        return()

    def _repo_chk(self, repo):
        def chkmnt():
            self.repo['mount'] = os.path.abspath(
                                    os.path.expanduser(
                                        self.repo['mount'].format(
                                            **self.strvars)))
            with open(os.devnull, 'w') as devnull:
                mntchk = subprocess.run(['findmnt',
                                         self.repo['mount']],
                                        stdout = devnull,
                                        stderr = devnull)
            if mntchk.returncode != 0:
                raise RuntimeError(('!! BAILING OUT; {0} isn\'t ' +
                                    'mounted !!').format(self.repo['mount']))
            return()
        def chkrsync():
            _port = 873
            _open = False
            self.repo['baseuri'] = re.sub('^\s*rsync://',
                                          '',
                                          self.repo['baseuri'].format(
                                                            **self.strvars),
                                          re.IGNORECASE)
            _raw_srv = self.repo['baseuri'].split('/')[0]
            _split_srv = re.sub('::.*$', '', _raw_srv).split(':')
            if len(_split_srv) >= 2:
                _port = _split_srv[1]
            for proto in (socket.AF_INET, socket.AF_INET6):
                s = socket.socket(proto, socket.SOCK_STREAM)
                chk = s.connect_ex((_split_srv[0], _port))
                if chk == 0:
                    _open = True
                    break
            if os.isatty(sys.stdin.fileno()):
                if not _open:
                    raise RuntimeError(('Rsync on host {0}:{1} is not ' +
                                        'accessible!').format(_split_srv[0],
                                                              _port))
                else:
                    exit()
            return()
        def chkdest():
            _dest = os.path.abspath(
                        os.path.expanduser(
                            self.cfg[repo]['destination'].format(
                                                            **self.strvars)))
            self.repo['destination'] = _dest
            os.makedirs(self.repo['destination'], exist_ok = True)
            return()
        def chkdest_files():
            for f in ('logfile', 'lockfile'):
                _dest = os.path.abspath(
                            os.path.expanduser(
                                self.repo[f].format(**self.strvars)))
                self.repo[f] = _dest
                os.makedirs(os.path.dirname(self.repo[f]), exist_ok = True)
            return()
        def chkmisc():
            # Odds and ends.
            pass
            return()
        # The Business-End(TM)
        chkmnt()
        chkrsync()
        chkdest()
        chkdest_files()
        chkmisc()
        return()

def main():
    m = MirrorMgr()
    m.sync()

if __name__ == '__main__':
    main()
