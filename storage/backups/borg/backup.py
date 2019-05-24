#!/usr/bin/env python3

# TODO: https://borgbackup.readthedocs.io/en/latest/internals/frontends.html
# will they EVER release a public API? for now we'll just use subprocess since
# we import it for various prep stuff anyways.
# TODO: change loglevel of borg itself in subprocess to match the argparse?
# --debug, --info (same as -v/--verbose), --warning, --error, --critical
# TODO: modify config to add repo to cfg for init? or add new operation, "add"

import argparse
import datetime
import json
import getpass
import logging
import logging.handlers
import os
import pwd
import re
# TODO: use borg module directly instead of subprocess?
import subprocess
import sys
import tempfile
# TODO: virtual env?
from lxml import etree  # A lot safer and easier to use than the stdlib xml module.
try:
    import pymysql  # not stdlib; "python-pymysql" in Arch's AUR
    has_mysql = True
except ImportError:
    has_mysql = False
try:
    # https://www.freedesktop.org/software/systemd/python-systemd/journal.html#journalhandler-class
    from systemd import journal
    has_systemd = True
except ImportError:
    has_systemd = False

### LOG LEVEL MAPPINGS ###
loglvls = {'critical': logging.CRITICAL,
           'error': logging.ERROR,
           'warning': logging.WARNING,
           'info': logging.INFO,
           'debug': logging.DEBUG}

### DEFAULT NAMESPACE ###
dflt_ns = 'http://git.square-r00t.net/OpTools/tree/storage/backups/borg/'


### THE GUTS ###
class Backup(object):
    def __init__(self, args):
        self.args = args
        self.ns = '{{{0}}}'.format(dflt_ns)
        if self.args['oper'] == 'restore':
            self.args['target_dir'] = os.path.abspath(os.path.expanduser(self.args['target_dir']))
            os.makedirs(self.args['target_dir'],
                        exist_ok = True,
                        mode = 0o700)
        self.repos = {}
        ### LOGGING ###
        # Thanks to:
        # https://web.archive.org/web/20170726052946/http://www.lexev.org/en/2013/python-logging-every-day/
        # https://stackoverflow.com/a/42604392
        # https://plumberjack.blogspot.com/2010/10/supporting-alternative-formatting.html
        # and user K900_ on r/python for entertaining my very silly question.
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(loglvls[self.args['loglevel']])
        _logfmt = logging.Formatter(fmt = ('{levelname}:{name}: {message} ({asctime}; {filename}:{lineno})'),
                                    style = '{',
                                    datefmt = '%Y-%m-%d %H:%M:%S')
        _journalfmt = logging.Formatter(fmt = '{levelname}:{name}: {message} ({filename}:{lineno})',
                                        style = '{',
                                        datefmt = '%Y-%m-%d %H:%M:%S')
        handlers = []
        if self.args['disklog']:
            os.makedirs(os.path.dirname(self.args['logfile']),
                        exist_ok = True,
                        mode = 0o700)
            # TODO: make the constraints for rotation in config?
            handlers.append(logging.handlers.RotatingFileHandler(self.args['logfile'],
                                                                 encoding = 'utf8',
                                                                 maxBytes = 100000,
                                                                 backupCount = 1))
        if self.args['verbose']:
            handlers.append(logging.StreamHandler())
        if has_systemd:
            h = journal.JournalHandler()
            h.setFormatter(_journalfmt)
            h.setLevel(loglvls[self.args['loglevel']])
            self.logger.addHandler(h)
        for h in handlers:
            h.setFormatter(_logfmt)
            h.setLevel(loglvls[self.args['loglevel']])
            self.logger.addHandler(h)
        ### END LOGGING ###
        self.logger.debug('BEGIN INITIALIZATION')
        ### CONFIG ###
        if not os.path.isfile(self.args['cfgfile']):
            self.logger.error('{0} does not exist'.format(self.args['cfgfile']))
            exit(1)
        try:
            with open(self.args['cfgfile'], 'rb') as f:
                self.cfg = etree.fromstring(f.read())
        except etree.XMLSyntaxError:
            self.logger.error('{0} is invalid XML'.format(self.args['cfgfile']))
            raise ValueError(('{0} does not seem to be valid XML. '
                              'See sample.config.xml for an example configuration.').format(self.args['cfgfile']))
        self.borgbin = self.cfg.attrib.get('borgpath', '/usr/bin/borg')
        ### CHECK ENVIRONMENT ###
        # If we're running from cron, we want to print errors to stdout.
        if os.isatty(sys.stdin.fileno()):
            self.cron = False
        else:
            self.cron = True
        self.logger.debug('END INITIALIZATION')
        self.buildRepos()

    def buildRepos(self):
        def getRepo(server, reponames = None):
            if not reponames:
                reponames = []
            repos = []
            for repo in server.findall('{0}repo'.format(self.ns)):
                if reponames and repo.attrib['name'] not in reponames:
                    continue
                r = {}
                for a in repo.attrib:
                    r[a] = repo.attrib[a]
                for e in ('path', 'exclude'):
                    r[e] = [i.text for i in repo.findall(self.ns + e)]
                for prep in repo.findall('{0}prep'.format(self.ns)):
                    if 'prep' not in r:
                        r['prep'] = []
                    if prep.attrib.get('inline', 'true').lower()[0] in ('0', 'f'):
                        with open(os.path.abspath(os.path.expanduser(prep.text)), 'r') as f:
                            r['prep'].append(f.read())
                    else:
                        r['prep'].append(prep.text)
                plugins = repo.find('{0}plugins'.format(self.ns))
                if plugins is not None:
                    r['plugins'] = {}
                    for plugin in plugins.findall('{0}plugin'.format(self.ns)):
                        pname = plugin.attrib['name']
                        r['plugins'][pname] = {'path': plugin.attrib.get('path'),
                                               'params': {}}
                        for param in plugin.findall('{0}param'.format(self.ns)):
                            paramname = param.attrib['key']
                            if param.attrib.get('json', 'false').lower()[0] in ('1', 't'):
                                r['plugins'][pname]['params'][paramname] = json.loads(param.text)
                            else:
                                r['plugins'][pname]['params'][paramname] = param.text
                repos.append(r)
            return(repos)
        self.logger.debug('VARS (before args cleanup): {0}'.format(vars(self)))
        self.args['repo'] = [i.strip() for i in self.args['repo'].split(',')]
        self.args['server'] = [i.strip() for i in self.args['server'].split(',')]
        if 'all' in self.args['repo']:
            self.args['repo'] = None
        if 'all' in self.args['server']:
            self.args['server'] = []
            for server in self.cfg.findall('{0}server'.format(self.ns)):
                # The server elements are uniquely constrained to the "target" attrib.
                # *NO TWO <server> ELEMENTS WITH THE SAME target= SHOULD EXIST.*
                self.args['server'].append(server.attrib['target'])
        for server in self.cfg.findall('{0}server'.format(self.ns)):
            sname = server.attrib['target']
            if sname not in self.args['server']:
                continue
            self.repos[sname] = {}
            for x in server.attrib:
                if x != 'target':
                    self.repos[sname][x] = server.attrib[x]
                self.repos[sname]['repos'] = getRepo(server, reponames = self.args['repo'])
        self.logger.debug('VARS (after args cleanup): {0}'.format(vars(self)))
        return()

    def createRepo(self):
        for server in self.repos:
            _env = os.environ.copy()
            # https://github.com/borgbackup/borg/issues/2273
            # https://borgbackup.readthedocs.io/en/stable/internals/frontends.html
            _env['LANG'] = 'en_US.UTF-8'
            _env['LC_CTYPE'] = 'en_US.UTF-8'
            if self.repos[server]['remote'].lower()[0] in ('1', 't'):
                _env['BORG_RSH'] = self.repos[server]['rsh']
            _user = self.repos[server].get('user', pwd.getpwuid(os.geteuid()).pw_name)
            for repo in self.repos[server]['repos']:
                self.logger.info('[{0}]: BEGIN INITIALIZATION'.format(repo['name']))
                _loc_env = _env.copy()
                if 'password' not in repo:
                    print('Password not supplied for {0}:{1}.'.format(server, repo['name']))
                    _loc_env['BORG_PASSPHRASE'] = getpass.getpass('Password (will NOT echo back): ')
                else:
                    _loc_env['BORG_PASSPHRASE'] = repo['password']
            _cmd = [self.borgbin,
                    '--log-json',
                    '--{0}'.format(self.args['loglevel']),
                    'init',
                    '-e', 'repokey']
            if self.repos[server]['remote'].lower()[0] in ('1', 't'):
                repo_tgt = '{0}@{1}'.format(_user, server)
            else:
                repo_tgt = os.path.abspath(os.path.expanduser(server))
            _cmd.append('{0}:{1}'.format(repo_tgt,
                                         repo['name']))
            self.logger.debug('VARS: {0}'.format(vars(self)))
            if not self.args['dryrun']:
                _out = subprocess.run(_cmd,
                                      env = _loc_env,
                                      stdout = subprocess.PIPE,
                                      stderr = subprocess.PIPE)
                _stdout = _out.stdout.decode('utf-8').strip()
                _stderr = _out.stderr.decode('utf-8').strip()
                _returncode = _out.returncode
                self.logger.debug('[{0}]: (RESULT) {1}'.format(repo['name'], _stdout))
                # sigh. borg uses stderr for verbose output.
                self.logger.debug('[{0}]: STDERR: ({2})\n{1}'.format(repo['name'],
                                                                     _stderr,
                                                                     ' '.join(_cmd)))
                if _returncode != 0:
                    self.logger.error(
                            '[{0}]: FAILED: {1}'.format(repo['name'], ' '.join(_cmd)))
                if _stderr != '' and self.cron and _returncode != 0:
                    self.logger.warning('Command {0} failed: {1}'.format(' '.join(_cmd),
                                                                         _stderr))
            self.logger.info('[{0}]: END INITIALIZATION'.format(repo['name']))
        return()

    def create(self):
        # TODO: support "--strip-components N"?
        self.logger.info('START: backup')
        for server in self.repos:
            _env = os.environ.copy()
            if self.repos[server]['remote'].lower()[0] in ('1', 't'):
                _env['BORG_RSH'] = self.repos[server].get('rsh', None)
            _env['LANG'] = 'en_US.UTF-8'
            _env['LC_CTYPE'] = 'en_US.UTF-8'
            _user = self.repos[server].get('user', pwd.getpwuid(os.geteuid()).pw_name)
            for repo in self.repos[server]['repos']:
                _loc_env = _env.copy()
                if 'password' not in repo:
                    print('Password not supplied for {0}:{1}.'.format(server, repo['name']))
                    _loc_env['BORG_PASSPHRASE'] = getpass.getpass('Password (will NOT echo back): ')
                else:
                    _loc_env['BORG_PASSPHRASE'] = repo['password']
                self.logger.info('[{0}]: BEGIN BACKUP: {1}'.format(server, repo['name']))
                if 'prep' in repo:
                    tmpdir = os.path.abspath(os.path.expanduser('~/.cache/.optools_backup'))
                    os.makedirs(tmpdir, exist_ok = True)
                    os.chmod(tmpdir, mode = 0o0700)
                    for idx, prep in enumerate(repo['prep']):
                        exec_tmp = tempfile.mkstemp(prefix = '_optools.backup.',
                                                    suffix = '._tmpexc',
                                                    text = True,
                                                    dir = tmpdir)[1]
                        os.chmod(exec_tmp, mode = 0o0700)
                        with open(exec_tmp, 'w') as f:
                            f.write(prep)
                        prep_out = subprocess.run([exec_tmp],
                                                  stdout = subprocess.PIPE,
                                                  stderr = subprocess.PIPE)
                        if prep_out.returncode != 0:
                            err = ('Prep job {0} ({1}) for server {2} (repo {3}) '
                                   'returned non-zero').format(idx, exec_tmp, server, repo)
                            logging.warning(err)
                            logging.debug('STDOUT: {0}'.format(prep_out.stdout.decode('utf-8')))
                            logging.debug('STDERR: {0}'.format(prep_out.stderr.decode('utf-8')))
                        else:
                            os.remove(exec_tmp)
                if 'plugins' in repo:
                    import importlib
                    _orig_path = sys.path
                    for plugin in repo['plugins']:
                        if repo['plugins'][plugin]['path']:
                            sys.path.insert(1, repo['plugins'][plugin]['path'] + sys.path)
                        optools_tmpmod = importlib.import_module(plugin, package = None)
                        if not repo['plugins'][plugin]['params']:
                            optools_tmpmod.Backup()
                        else:
                            optools_tmpmod.Backup(**repo['plugins'][plugin]['params'])
                        del(sys.modules[plugin])
                        del(optools_tmpmod)
                        sys.path = _orig_path
                # This is where we actually do the thing.
                _cmd = [self.borgbin,
                        '--log-json',
                        '--{0}'.format(self.args['loglevel']),
                        'create',
                        '--stats']
                if 'compression' in repo:
                    _cmd.extend(['--compression', repo['compression']])
                if 'exclude' in repo:
                    for e in repo['exclude']:
                        _cmd.extend(['--exclude', e])
                if self.repos[server]['remote'].lower()[0] in ('1', 't'):
                    repo_tgt = '{0}@{1}'.format(_user, server)
                else:
                    repo_tgt = os.path.abspath(os.path.expanduser(server))
                _cmd.append('{0}:{1}::{2}'.format(repo_tgt,
                                                  repo['name'],
                                                  self.args['archive']))
                for p in repo['path']:
                    _cmd.append(p)
                self.logger.debug('VARS: {0}'.format(vars()))
                # We don't use self.cmdExec() here because we want to explicitly
                # pass the env and format the log line differently.
                self.logger.debug('[{0}]: Running command: {1}'.format(repo['name'],
                                                                       ' '.join(_cmd)))
                if not self.args['dryrun']:
                    _out = subprocess.run(_cmd,
                                          env = _loc_env,
                                          stdout = subprocess.PIPE,
                                          stderr = subprocess.PIPE)
                    _stdout = _out.stdout.decode('utf-8').strip()
                    _stderr = _out.stderr.decode('utf-8').strip()
                    _returncode = _out.returncode
                    self.logger.debug('[{0}]: (RESULT) {1}'.format(repo['name'], _stdout))
                    self.logger.debug('[{0}]: STDERR: ({2})\n{1}'.format(repo['name'],
                                                                         _stderr,
                                                                         ' '.join(
                                                                                 _cmd)))
                    if _returncode != 0:
                        self.logger.error(
                                '[{0}]: FAILED: {1}'.format(repo['name'], ' '.join(_cmd)))
                    if _stderr != '' and self.cron and _returncode != 0:
                        self.logger.warning('Command {0} failed: {1}'.format(' '.join(_cmd),
                                                                             _stderr))
                    del (_loc_env['BORG_PASSPHRASE'])
                self.logger.info('[{0}]: END BACKUP'.format(repo['name']))
        self.logger.info('END: backup')
        return()

    def restore(self):
        # TODO: support "--strip-components N"?
        # TODO: support add'l args?
        # https://borgbackup.readthedocs.io/en/stable/usage/extract.html
        orig_dir = os.getcwd()
        self.logger.info('START: restore')
        self.args['target_dir'] = os.path.abspath(os.path.expanduser(self.args['target_dir']))
        os.makedirs(self.args['target_dir'], exist_ok = True)
        os.chmod(self.args['target_dir'], mode = 0o0700)
        for server in self.repos:
            _env = os.environ.copy()
            if self.repos[server]['remote'].lower()[0] in ('1', 't'):
                _env['BORG_RSH'] = self.repos[server].get('rsh', None)
            _env['LANG'] = 'en_US.UTF-8'
            _env['LC_CTYPE'] = 'en_US.UTF-8'
            _user = self.repos[server].get('user', pwd.getpwuid(os.geteuid()).pw_name)
            server_dir = os.path.join(self.args['target_dir'], server)
            for repo in self.repos[server]['repos']:
                _loc_env = _env.copy()
                if 'password' not in repo:
                    print('Password not supplied for {0}:{1}.'.format(server, repo['name']))
                    _loc_env['BORG_PASSPHRASE'] = getpass.getpass('Password (will NOT echo back): ')
                else:
                    _loc_env['BORG_PASSPHRASE'] = repo['password']
                if len(self.repos[server]) > 1:
                    dest_dir = os.path.join(server_dir, repo['name'])
                else:
                    dest_dir = server_dir
                os.makedirs(dest_dir, exist_ok = True)
                os.chmod(dest_dir, mode = 0o0700)
                os.chdir(dest_dir)
                self.logger.info('[{0}]: BEGIN RESTORE'.format(repo['name']))
                _cmd = [self.borgbin,
                        '--log-json',
                        '--{0}'.format(self.args['loglevel']),
                        'extract']
                if self.repos[server]['remote'].lower()[0] in ('1', 't'):
                    repo_tgt = '{0}@{1}'.format(_user, server)
                else:
                    repo_tgt = os.path.abspath(os.path.expanduser(server))
                _cmd.append('{0}:{1}::{2}'.format(repo_tgt,
                                                  repo['name'],
                                                  self.args['archive']))
                if self.args['archive_path']:
                    _cmd.append(self.args['archive_path'])
                self.logger.debug('VARS: {0}'.format(vars(self)))
                self.logger.debug('[{0}]: Running command: {1}'.format(repo['name'],
                                                                       ' '.join(_cmd)))
                if not self.args['dryrun']:
                    _out = subprocess.run(_cmd,
                                          env = _loc_env,
                                          stdout = subprocess.PIPE,
                                          stderr = subprocess.PIPE)
                    _stdout = _out.stdout.decode('utf-8').strip()
                    _stderr = _out.stderr.decode('utf-8').strip()
                    _returncode = _out.returncode
                    self.logger.debug('[{0}]: (RESULT) {1}'.format(repo['name'], _stdout))
                    self.logger.debug('[{0}]: STDERR: ({2})\n{1}'.format(repo['name'],
                                                                         _stderr,
                                                                         ' '.join(_cmd)))
                    if _returncode != 0:
                        self.logger.error('[{0}]: FAILED: {1}'.format(repo['name'],
                                                                      ' '.join(_cmd)))
                    if _stderr != '' and self.cron and _returncode != 0:
                        self.logger.warning('Command {0} failed: {1}'.format(' '.join(_cmd),
                                                                             _stderr))
                self.logger.info('[{0}]: END RESTORE'.format(repo['name']))
                os.chdir(orig_dir)
        self.logger.info('END: restore')
        return()

    def listRepos(self):
        def objPrinter(d, indent = 0):
            for k, v in d.items():
                if k == 'name':
                    continue
                if k.lower() in ('password', 'path', 'exclude', 'prep', 'plugins', 'params', 'compression'):
                    keyname = k.title()
                else:
                    keyname = k
                if isinstance(v, list):
                    for i in v:
                        print('\033[1m{0}{1}:\033[0m {2}'.format(('\t' * indent),
                                                                 keyname,
                                                                 i))
                elif isinstance(v, dict):
                    print('\033[1m{0}{1}:\033[0m'.format(('\t' * indent),
                                                         keyname))
                    objPrinter(v, indent = (indent + 1))
                else:
                    print('\033[1m{0}{1}:\033[0m {2}'.format(('\t' * indent),
                                                             keyname,
                                                             v))
            return()
        print('\n\033[1mCurrently configured repositories are:\033[0m\n')
        for server in self.repos:
            print('\033[1mTarget:\033[0m {0}'.format(server))
            print('\033[1mRepositories:\033[0m')
            for r in self.repos[server]['repos']:
                if not self.args['verbose']:
                    print('\t\t{0}'.format(r['name']))
                else:
                    print('\t\t\033[1mName:\033[0m {0}'.format(r['name']))
                    print('\033[1m\t\tDetails:\033[0m')
                    objPrinter(r, indent = 3)
                    print()
        return()

    def printer(self):
        # TODO: better alignment. https://stackoverflow.com/a/5676884
        _results = self.lister()
        timefmt = '%Y-%m-%dT%H:%M:%S.%f'
        if not self.args['archive']:
            # It's a listing of archives
            for server in _results:
                print('\033[1mTarget:\033[0m {0}'.format(server))
                print('\033[1mRepositories:\033[0m')
                # Normally this is a list everywhere else. For results, however, it's a dict.
                for repo in _results[server]:
                    print('\t\033[1m{0}:\033[0m'.format(repo))
                    print('\t\t\033[1mSnapshot\t\tTimestamp\033[0m')
                    for archive in _results[server][repo]:
                        print('\t\t{0}\t\t{1}'.format(archive['name'],
                                                      datetime.datetime.strptime(archive['time'], timefmt)))
            print()
        else:
            # It's a listing inside an archive
            if self.args['verbose']:
                _archive_fields = ['Mode', 'Owner', 'Size', 'Timestamp', 'Path']
                for server in _results:
                    print('\033[1mTarget:\033[0m {0}'.format(server))
                    print('\033[1mRepositories:\033[0m')
                    for repo in _results[server]:
                        print('\t\033[1m{0}:\033[0m'.format(repo))
                        print(('\t\t\033[1m'
                               '{0[0]:<10}\t'
                               '{0[1]:<10}\t'
                               '{0[2]:<10}\t'
                               '{0[3]:<19}\t'
                               '{0[4]}'
                               '\033[0m').format(_archive_fields))
                        for file in _results[server][repo]:
                            file['mtime'] = datetime.datetime.strptime(file['mtime'], timefmt)
                            print(('\t\t'
                                   '{mode:<10}\t'
                                   '{user:<10}\t'
                                   '{size:<10}\t'
                                   '{mtime}\t'
                                   '{path}').format(**file))
            else:
                for server in _results:
                    print('\033[1mTarget:\033[0m {0}'.format(server))
                    print('\033[1mRepositories:\033[0m')
                    for repo in _results[server]:
                        print('\t\033[1m{0}:\033[0m'.format(repo))
                        for file in _results[server][repo]:
                            print(file['path'])
        return()

    def lister(self):
        output = {}
        self.logger.debug('START: lister')
        for server in self.repos:
            output[server] = {}
            _env = os.environ.copy()
            if self.repos[server]['remote'].lower()[0] in ('1', 't'):
                _env['BORG_RSH'] = self.repos[server].get('rsh', None)
            _env['LANG'] = 'en_US.UTF-8'
            _env['LC_CTYPE'] = 'en_US.UTF-8'
            _user = self.repos[server].get('user', pwd.getpwuid(os.geteuid()).pw_name)
            for repo in self.repos[server]['repos']:
                _loc_env = _env.copy()
                if 'password' not in repo:
                    print('Password not supplied for {0}:{1}.'.format(server, repo['name']))
                    _loc_env['BORG_PASSPHRASE'] = getpass.getpass('Password (will NOT echo back): ')
                else:
                    _loc_env['BORG_PASSPHRASE'] = repo['password']
                if self.repos[server]['remote'].lower()[0] in ('1', 't'):
                    repo_tgt = '{0}@{1}'.format(_user, server)
                else:
                    repo_tgt = os.path.abspath(os.path.expanduser(server))
                _cmd = [self.borgbin,
                        '--log-json',
                        '--{0}'.format(self.args['loglevel']),
                        'list',
                        ('--json-lines' if self.args['archive'] else '--json')]
                _cmd.append('{0}:{1}{2}'.format(repo_tgt,
                                                repo['name'],
                                                ('::{0}'.format(self.args['archive']) if self.args['archive']
                                                 else '')))
            if not self.args['dryrun']:
                _out = subprocess.run(_cmd,
                                      env = _loc_env,
                                      stdout = subprocess.PIPE,
                                      stderr = subprocess.PIPE)
                _stdout = [i.strip() for i in _out.stdout.decode('utf-8').splitlines()]
                _stderr = _out.stderr.decode('utf-8').strip()
                _returncode = _out.returncode
                if self.args['archive']:
                    output[server][repo['name']] = [json.loads(i) for i in _stdout.splitlines()]
                else:
                    output[repo['name']] = json.loads(_stdout)['archives']
                self.logger.debug('[{0}]: (RESULT) {1}'.format(repo['name'],
                                                               '\n'.join(_stdout)))
                self.logger.debug('[{0}]: STDERR: ({2}) ({1})'.format(repo['name'],
                                                                      _stderr,
                                                                      ' '.join(_cmd)))
                if _stderr != '' and self.cron and _returncode != 0:
                    self.logger.warning('Command {0} failed: {1}'.format(' '.join(_cmd),
                                                                         _stderr))
            if not self.args['archive']:
                if self.args['numlimit'] > 0:
                    if self.args['old']:
                        output[server][repo['name']] = output[server][repo['name']][:self.args['numlimit']]
                    else:
                        output[server][repo['name']] = list(reversed(
                                                                output[server][repo['name']]))[:self.args['numlimit']]
            if self.args['invert']:
                output[server][repo['name']] = reversed(output[server][repo['name']])
        self.logger.debug('END: lister')
        return(output)


def printMoarHelp():
    _helpstr = ('\n\tNOTE: Sorting only applies to listing archives, NOT the contents!\n\n'
                'In order to efficiently display results, there are several options to handle it. '
                'Namely, these are:\n\n\t\t'
                    '-s/--sort [direction]\n\t\t'
                    '-l/--limit [number]\n\t\t'
                    '-x/--invert\n\n'
                'For example, if you want to list the 5 most recently *taken* snapshots, you would use:\n\n\t\t'
                    '-l 5\n\n'
                'If you would want those SAME results SORTED in the reverse order (i.e. the 5 most recently '
                'taken snapshots sorted from newest to oldest), then it would be: \n\n\t\t'
                    '-l 5 -x\n\n'
                'Lastly, if you wanted to list the 7 OLDEST TAKEN snapshots in reverse order '
                '(that is, sorted from newest to oldest), that\'d be:\n\n\t\t'
                    '-o -l 7 -x\n')
    print(_helpstr)
    exit(0)


def parseArgs():
    ### DEFAULTS ###
    _date = datetime.datetime.now().strftime("%Y_%m_%d.%H_%M")
    _logfile = '/var/log/borg/{0}'.format(_date)
    _cfgfile = os.path.abspath(
            os.path.join(os.path.expanduser('~'),
                         '.config',
                         'optools',
                         'backup.xml'))
    _defloglvl = 'info'
    ######
    args = argparse.ArgumentParser(description = 'Backups manager',
                                   epilog = ('TIP: this program has context-specific help. '
                                             'e.g. try "%(prog)s list --help"'))
    args.add_argument('-c', '--config',
                      dest = 'cfgfile',
                      default = _cfgfile,
                      help = (
                          'The path to the config file. '
                          'Default: \033[1m{0}\033[0m'.format(_cfgfile)))
    args.add_argument('-Ll', '--loglevel',
                      dest = 'loglevel',
                      default = _defloglvl,
                      choices = list(loglvls.keys()),
                      help = (
                          'The level of logging to perform. \033[1mWARNING:\033[0m \033[1mdebug\033[0m will '
                          'log VERY sensitive information such as passwords! '
                          'Default: \033[1m{0}\033[0m'.format(_defloglvl)))
    args.add_argument('-Ld', '--log-to-disk',
                      dest = 'disklog',
                      action = 'store_true',
                      help = (
                          'If specified, log to a specific file (-Lf/--logfile) instead of the system logger.'))
    args.add_argument('-Lf', '--logfile',
                      dest = 'logfile',
                      default = _logfile,
                      help = (
                          'The path to the logfile, only used if -Ld/--log-to-disk is specified. '
                          'Default: \033[1m{0}\033[0m (dynamic)').format(_logfile))
    args.add_argument('-v', '--verbose',
                      dest = 'verbose',
                      action = 'store_true',
                      help = ('If specified, log messages will be printed to STDERR in addition to the other '
                              'configured log system(s), and verbosity for printing functions is increased. '
                              '\033[1mWARNING:\033[0m This may display VERY sensitive information such as passwords!'))
    ### ARGS FOR ALL OPERATIONS ###
    commonargs = argparse.ArgumentParser(add_help = False)
    commonargs.add_argument('-r', '--repo',
                            dest = 'repo',
                            default = 'all',
                            help = ('The repository to perform the operation for. '
                                    'The default is \033[1mall\033[0m, a special value that specifies all known '
                                    'repositories. Can also accept a comma-separated list.'))
    commonargs.add_argument('-S', '--server',
                            dest = 'server',
                            default = 'all',
                            help = ('The server to perform the operation for. '
                                    'The default is \033[1mall\033[0m, a special value that specifies all known '
                                    'servers. Can also accept a comma-separated list.'))
    fileargs = argparse.ArgumentParser(add_help = False)
    fileargs.add_argument('-a', '--archive',
                          default = _date,
                          dest = 'archive',
                          help = ('The name of the archive/snapshot. '
                                  'Default: \033[1m{0}\033[0m (dynamic)').format(_date))
    remoteargs = argparse.ArgumentParser(add_help = False)
    remoteargs.add_argument('-d', '--dry-run',
                            dest = 'dryrun',
                            action = 'store_true',
                            help = ('Act as if we are performing tasks, but none will actually be executed '
                                    '(useful for testing logging)'))
    ### OPERATIONS ###
    subparsers = args.add_subparsers(help = 'Operation to perform',
                                     dest = 'oper')
    backupargs = subparsers.add_parser('backup',
                                       help = 'Perform a backup.',
                                       parents = [commonargs,
                                                  remoteargs,
                                                  fileargs])
    listargs = subparsers.add_parser('list',
                                     help = 'List available backups.',
                                     parents = [commonargs, remoteargs])
    listrepoargs = subparsers.add_parser('listrepos',
                                         help = ('List availabile/configured repositories.'),
                                         parents = [commonargs])
    initargs = subparsers.add_parser('init',
                                     help = 'Initialise a repository.',
                                     parents = [commonargs, remoteargs])
    rstrargs = subparsers.add_parser('restore',
                                     help = ('Restore ("extract") an archive.'),
                                     parents = [commonargs,
                                                remoteargs,
                                                fileargs])
    cvrtargs = subparsers.add_parser('convert',
                                     help = ('Convert the legacy JSON format to the new XML format and quit'))
    ### OPERATION-SPECIFIC OPTIONS ###
    # CREATE ("backup") #
    # DISPLAY/OUTPUT ("list") #
    listargs.add_argument('-a', '--archive',
                          dest = 'archive',
                          default = False,
                          help = 'If specified, will list the *contents* of the given archive name.')
    listargs.add_argument('-l', '--limit',
                          dest = 'numlimit',
                          type = int,
                          default = '5',
                          help = ('If specified, constrain the outout to this number of results each repo. '
                                  'Default is \033[1m5\033[0m, use 0 for unlimited. See \033[1m-H/--list-help\033[0m'))
    listargs.add_argument('-s', '--sort',
                          dest = 'sortby',
                          choices = ['newest', 'oldest'],
                          default = 'oldest',
                          help = ('The order to sort the results by. See \033[1m-H/--list-help\033[0m. '
                                  'Default: \033[1moldest\033[0m'))
    listargs.add_argument('-x', '--invert',
                          dest = 'invert',
                          action = 'store_true',
                          help = 'Invert the order of results. See \033[1m-H/--list-help\033[0m.')
    listargs.add_argument('-o', '--old',
                          dest = 'old',
                          action = 'store_true',
                          help = ('Instead of grabbing the latest results, grab the earliest results. This differs '
                                  'from \033[1m-s/--sort\033[0m. See \033[1m-H/--list-help\033[0m.'))
    listargs.add_argument('-H', '--list-help',
                          dest = 'moarhelp',
                          action = 'store_true',
                          help = ('Print extended information about how to '
                                  'manage the output of listing and exit.'))
    ## EXTRACT ("restore")
    rstrargs.add_argument('-p', '--path',
                          dest = 'archive_path',
                          help = ('If specified, only restore this specific path (and any subpaths).'))
    rstrargs.add_argument('-t', '--target',
                          required = True,
                          dest = 'target_dir',
                          help = ('The path to the directory where the restore should be dumped to. It is '
                                  'recommended to not restore to the same directory that the archive is taken from. '
                                  'A subdirectory will be created for each server.'
                                  'If multiple repos (or "all") are provided, subdirectories will be created per '
                                  'repo under their respective server(s).'))
    return (args)

def convertConf(cfgfile):
    oldcfgfile = re.sub('\.xml$', '.json', cfgfile)
    try:
        with open(oldcfgfile, 'r') as f:
            oldcfg = json.load(f)
    except json.decoder.JSONDecodeError:
        # It's not JSON. It's either already XML or invalid config.
        return(cfgfile)
    # Switched from JSON to XML, so we need to do some basic conversion.
    newfname = re.sub('\.json$', '.xml', os.path.basename(cfgfile))
    newcfg = os.path.join(os.path.dirname(cfgfile),
                          newfname)
    if os.path.exists(newcfg):
        # Do nothing. We don't want to overwrite an existing config
        # and we'll assume it's an already-done conversion.
        return(newcfg)
    print(('It appears that you are still using the legacy JSON format. '
           'We will attempt to convert it to the new XML format ({0}) but it may '
           'require modifications, especially if you are using any prep functions as those are not '
           'converted automatically. See sample.config.xml for an example of this.').format(newcfg))
    cfg = etree.Element('borg')
    # The old format only supported one server.
    server = etree.Element('server')
    server.attrib['target'] = oldcfg['config']['host']
    server.attrib['remote'] = 'true'
    server.attrib['rsh'] = oldcfg['config']['ctx']
    server.attrib['user'] = oldcfg['config'].get('user', pwd.getpwnam(os.geteuid()).pw_name)
    for r in oldcfg['repos']:
        repo = etree.Element('repo')
        repo.attrib['name'] = r
        repo.attrib['password'] = oldcfg['repos'][r]['password']
        for p in oldcfg['repos'][r]['paths']:
            path = etree.Element('path')
            path.text = p
            repo.append(path)
        for e in oldcfg['repos'][r].get('excludes', []):
            path = etree.Element('exclude')
            path.text = e
            repo.append(path)
        server.append(repo)
    cfg.append(server)
    # Build the full XML spec.
    namespaces = {None: dflt_ns,
                  'xsi': 'http://www.w3.org/2001/XMLSchema-instance'}
    xsi = {('{http://www.w3.org/2001/'
            'XMLSchema-instance}schemaLocation'): ('http://git.square-r00t.net/OpTools/plain/'
                                                   'storage/backups/borg/config.xsd')}
    genname = 'LXML (http://lxml.de/)'
    root = etree.Element('borg', nsmap = namespaces, attrib = xsi)
    root.append(etree.Comment(('Generated by {0} on {1} from {2} via {3}').format(sys.argv[0],
                                                                                  datetime.datetime.now(),
                                                                                  oldcfgfile,
                                                                                  genname)))
    root.append(etree.Comment('THIS FILE CONTAINS SENSITIVE INFORMATION. SHARE/SCRUB WISELY.'))
    for x in cfg:
        root.append(x)
    # Write out the file to disk.
    xml = etree.ElementTree(root)
    with open(newcfg, 'wb') as f:
        xml.write(f,
                  xml_declaration = True,
                  encoding = 'utf-8',
                  pretty_print = True)
    # Return the new config's path.
    return(newcfg)


def main():
    rawargs = parseArgs()
    parsedargs = rawargs.parse_args()
    args = vars(parsedargs)
    args['cfgfile'] = os.path.abspath(os.path.expanduser(args['cfgfile']))
    if not args['oper']:
        rawargs.print_help()
        exit(0)
    if 'moarhelp' in args.keys() and args['moarhelp']:
        printMoarHelp()
    if args['oper'] == 'convert':
        convertConf(args['cfgfile'])
        return()
    else:
        if not os.path.isfile(args['cfgfile']):
            oldfile = re.sub('\.xml$', '.json', args['cfgfile'])
            if os.path.isfile(oldfile):
                try:
                    with open(oldfile, 'r') as f:
                        json.load(f)
                        args['cfgfile'] = convertConf(args['cfgfile'])
                except json.decoder.JSONDecodeError:
                    # It's not JSON. It's either already XML or invalid config.
                    pass
    if not os.path.isfile(args['cfgfile']):
        raise OSError('{0} does not exist'.format(args['cfgfile']))
    # The "Do stuff" part
    bak = Backup(args)
    if args['oper'] == 'list':
        bak.printer()
    elif args['oper'] == 'listrepos':
        bak.listRepos()
    elif args['oper'] == 'backup':
        bak.create()
    elif args['oper'] == 'init':
        bak.createRepo()
    elif args['oper'] == 'restore':
        bak.restore()
    return()


if __name__ == '__main__':
    main()
