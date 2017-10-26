#!/usr/bin/env python3

# TODO: https://borgbackup.readthedocs.io/en/latest/internals/frontends.html
# will they EVER release a public API? for now we'll just use subprocess since
# we import it for various prep stuff anyways.

import argparse
import configparser
import datetime
import json
import logging
import logging.handlers
import os
import subprocess
import sys
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

### THE GUTS ###
class Backup(object):
    def __init__(self, args):
        self.args = args
        ### DIRECTORIES ###
        if self.args['oper'] == 'backup':
            for d in (self.args['mysqldir'], self.args['stagedir']):
                os.makedirs(d, exist_ok = True, mode = 0o700)
        ### LOGGING ###
        # Thanks to:
        # https://web.archive.org/web/20170726052946/http://www.lexev.org/en/2013/python-logging-every-day/
        # https://stackoverflow.com/a/42604392
        # https://plumberjack.blogspot.com/2010/10/supporting-alternative-formatting.html
        # and user K900_ on r/python for entertaining my very silly question.
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(loglvls[self.args['loglevel']])
        _logfmt = logging.Formatter(fmt = '{levelname}:{name}: {message} ({asctime}; {filename}:{lineno})',
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
        self.logger.debug('BEGIN INITIALIZATION')
        ### CONFIG ###
        if not os.path.isfile(self.args['cfgfile']):
            self.logger.error('{0} does not exist'.format(self.args['cfgfile']))
            exit(1)
        with open(self.args['cfgfile'], 'r') as f:
            self.cfg = json.loads(f.read())
        ### END LOGGING ###
        ### ARGS CLEANUP ###
        self.logger.debug('VARS (before args cleanup): {0}'.format(vars()))
        self.args['repo'] = [i.strip() for i in self.args['repo'].split(',')]
        if 'all' in self.args['repo']:
            self.args['repo'] = list(self.cfg['repos'].keys())
        for r in self.args['repo'][:]:
            if r == 'all':
                self.args['repo'].remove(r)
            elif r not in self.cfg['repos'].keys():
                self.logger.warning('Repository {0} is not configured; skipping.'.format(r))
                self.args['repo'].remove(r)
        self.logger.debug('VARS (after args cleanup): {0}'.format(vars()))
        self.logger.debug('END INITIALIZATION')
        ### CHECK ENVIRONMENT ###
        # If we're running from cron, we want to print errors to stdout.
        if os.isatty(sys.stdin.fileno()):
            self.cron = False
        else:
            self.cron = True
        ### END INIT ###
        
    def cmdExec(self, cmd, stdoutfh = None):
        self.logger.debug('Running command: {0}'.format(' '.join(cmd)))
        if self.args['dryrun']:
            return()  # no-op
        if stdoutfh:
            _cmd = subprocess.run(cmd, stdout = stdoutfh, stderr = subprocess.PIPE)
        else:
            _cmd = subprocess.run(cmd,
                                  stdout = subprocess.PIPE,
                                  stderr = subprocess.PIPE)
            _out = _cmd.stdout.decode('utf-8').strip()
        _err = _cmd.stderr.decode('utf-8').strip()
        _returncode = _cmd.returncode
        if _returncode != 0:
            self.logger.error('STDERR: ({1})\n{0}'.format(_err, ' '.join(cmd)))
        if _err != '' and self.cron:
            self.logger.warning('Command {0} failed: {1}'.format(' '.join(cmd), _err)
        return()
    
    def createRepo(self):
        _env = os.environ.copy()
        _env['BORG_RSH'] = self.cfg['config']['ctx']
        for r in self.args['repo']:
            self.logger.info('[{0}]: BEGIN INITIALIZATION'.format(r))
            _cmd = ['borg',
                    'init',
                    '-v',
                    '{0}@{1}:{2}'.format(self.cfg['config']['user'],
                                         self.cfg['config']['host'],
                                         r)]
            _env['BORG_PASSPHRASE'] = self.cfg['repos'][r]['password']
            # We don't use self.cmdExec() here either because
            # again, custom env, etc.
            self.logger.debug('VARS: {0}'.format(vars()))
            if not self.args['dryrun']:
                _out = subprocess.run(_cmd,
                                      env = _env,
                                      stdout = subprocess.PIPE,
                                      stderr = subprocess.PIPE)
                _stdout = _out.stdout.decode('utf-8').strip()
                _stderr = _out.stderr.decode('utf-8').strip()
                _returncode = _out.returncode
                self.logger.debug('[{0}]: (RESULT) {1}'.format(r, _stdout))
                # sigh. borg uses stderr for verbose output.
                self.logger.debug('[{0}]: STDERR: ({2})\n{1}'.format(r,
                                                                     _stderr,
                                                                     ' '.join(_cmd)))
                if _returncode != 0:
                    self.logger.error('[{0}]: FAILED: {1}'.format(r, ' '.join(_cmd)))
                if _err != '' and self.cron and _returncode != 0:
                    self.logger.warning('Command {0} failed: {1}'.format(' '.join(cmd), _err)
            del(_env['BORG_PASSPHRASE'])
            self.logger.info('[{0}]: END INITIALIZATION'.format(r))
        return()

    def create(self):
        _env = os.environ.copy()
        _env['BORG_RSH'] = self.cfg['config']['ctx']
        self.logger.info('START: backup')
        for r in self.args['repo']:
            self.logger.info('[{0}]: BEGIN BACKUP'.format(r))
            if 'prep' in self.cfg['repos'][r].keys():
                for prep in self.cfg['repos'][r]['prep']:
                    self.logger.info('[{0}]: Running prepfunc {1}'.format(r, prep))
                    eval('self.{0}'.format(prep))  # I KNOW, IT'S TERRIBLE. so sue me.
                    self.logger.info('[{0}]: Finished prepfunc {1}'.format(r, prep))
            _cmd = ['borg',
                    'create',
                    '-v', '--stats',
                    '--compression', 'lzma,9']
            if 'excludes' in self.cfg['repos'][r].keys():
                for e in self.cfg['repos'][r]['excludes']:
                    _cmd.extend(['--exclude', e])
            _cmd.append('{0}@{1}:{2}::{3}'.format(self.cfg['config']['user'],
                                                  self.cfg['config']['host'],
                                                  r,
                                                  self.args['archive']))
            for p in self.cfg['repos'][r]['paths']:
                _cmd.append(p)
            _env['BORG_PASSPHRASE'] = self.cfg['repos'][r]['password']
            self.logger.debug('VARS: {0}'.format(vars()))
            # We don't use self.cmdExec() here because we want to explicitly pass the env
            # and format the log line differently.
            self.logger.debug('[{0}]: Running command: {1}'.format(r, ' '.join(_cmd)))
            if not self.args['dryrun']:
                _out = subprocess.run(_cmd,
                                      env = _env,
                                      stdout = subprocess.PIPE,
                                      stderr = subprocess.PIPE)
                _stdout = _out.stdout.decode('utf-8').strip()
                _stderr = _out.stderr.decode('utf-8').strip()
                _returncode = _out.returncode
                self.logger.debug('[{0}]: (RESULT) {1}'.format(r, _stdout))
                self.logger.error('[{0}]: STDERR: ({2})\n{1}'.format(r,
                                                                     _stderr,
                                                                     ' '.join(_cmd)))
                if _returncode != 0:
                    self.logger.error('[{0}]: FAILED: {1}'.format(r, ' '.join(_cmd)))
                if _err != '' and self.cron and _returncode != 0:
                    self.logger.warning('Command {0} failed: {1}'.format(' '.join(cmd), _err)
                del(_env['BORG_PASSPHRASE'])
            self.logger.info('[{0}]: END BACKUP'.format(r))
        self.logger.info('END: backup')
        return()

    def miscBak(self, pkgr):
        self.logger.info('BEGIN: miscBak()')
        _cmd = None
        for p in os.environ['PATH'].split(':'):
            d = os.path.expanduser(p)
            if os.path.isfile(os.path.join(d, pkgr)):
                _pkgr = pkgr
                self.logger.debug('Package tool found at {0}'.format(_pkgr))
            else:
                _pkgr = 'pacman'
                self.logger.debug('Using {0} as package tool'.format(_pkgr))
        with open(os.path.join(self.args['stagedir'], 'pkg.lst'), 'w') as f:
            _cmd = [_pkgr,
                    '-Qet',
                    '--color',
                    'never']
            self.cmdExec(_cmd, stdoutfh = f)
        self.logger.info('END: miscBak()')
        return()

    def mysqlBak(self):
        self.logger.info('BEGIN: mysqlBak()')
        if not has_mysql:
            self.logger.error('You need to install the PyMySQL module to back up MySQL databases. Skipping.')
            return()
        # These are mysqldump options shared by ALL databases
        _mysqlopts = ['--routines',
                      '--add-drop-database',
                      '--add-drop-table',
                      '--allow-keywords',
                      '--complete-insert',
                      '--create-options',
                      '--extended-insert']
        _DBs = []
        _mycnf = os.path.expanduser(os.path.join('~', '.my.cnf'))
        if not os.path.isfile(_mycnf):
            exit('{0}: ERROR: Cannot get credentials for MySQL (cannot find ~/.my.cnf)!')
        _mycfg = configparser.ConfigParser()
        _mycfg._interpolation = configparser.ExtendedInterpolation()
        _mycfg.read(_mycnf)
        _sqlcfg = {s:dict(_mycfg.items(s)) for s in _mycfg.sections()}
        if 'host' not in _sqlcfg.keys():
            _socketpath = '/var/run/mysqld/mysqld.sock'  # correct for Arch, YMMV.
            _mysql = pymysql.connect(unix_socket = _socketpath,
                                     user = _sqlcfg['client']['user'],
                                     passwd = _sqlcfg['client']['password'])
        else:
            _mysql = pymysql.connect(host = _sqlcfg['client']['host'],
                                     user = _sqlcfg['client']['user'],
                                     port = _sqlcfg['client']['port'],
                                     passwd = _sqlcfg['client']['password'])
        _cur = _mysql.cursor()
        _cur.execute('SHOW DATABASES')
        for row in _cur.fetchall():
            _DBs.append(row[0])
        self.logger.debug('Databases: {0}'.format(', '.join(_DBs)))
        for db in _DBs:
            _cmd = ['mysqldump',
                    '--result-file={0}.sql'.format(os.path.join(mysqldir, db))]
            # These are database-specific options
            if db in ('information_schema', 'performance_schema'):
                _cmd.append('--skip-lock-tables')
            elif db == 'mysql':
                _cmd.append('--flush-privileges')
            _cmd.extend(_mysqlopts)
            _cmd.append(db)
            self.cmdExec(_cmd)
        self.logger.info('END: mysqlBak()')
        return()

    def listRepos(self):
        print('\n\033[1mCurrently configured repositories are:\033[0m\n')
        print('\t{0}\n'.format(', '.join(self.cfg['repos'].keys())))
        if self.args['verbose']:
            print('\033[1mDETAILS:\033[0m\n')
            for r in self.args['repo']:
                print('\t\033[1m{0}:\033[0m\n\t\t\033[1mPath(s):\033[0m\t'.format(r.upper()), end = '')
                for p in self.cfg['repos'][r]['paths']:
                    print(p, end = ' ')
                if 'prep' in self.cfg['repos'][r].keys():
                    print('\n\t\t\033[1mPrep:\033[0m\t\t', end = '')
                    for p in self.cfg['repos'][r]['prep']:
                        print(p, end = ' ')
                if 'excludes' in self.cfg['repos'][r].keys():
                    print('\n\t\t\033[1mExclude(s):\033[0m\t', end = '')
                    for p in self.cfg['repos'][r]['excludes']:
                        print(p, end = ' ')
                print('\n')
        return()

    def printer(self):
        # TODO: better alignment. https://stackoverflow.com/a/5676884
        _results = self.lister()
        if not self.args['archive']:  # It's a listing of archives
            print('\033[1mREPO:\tSNAPSHOT:\t\tTIMESTAMP:\033[0m\n')
            for r in _results.keys():
                print(r, end = '')
                for line in _results[r]:
                    _snapshot = line.split()
                    print('\t{0}\t\t{1}'.format(_snapshot[0], ' '.join(_snapshot[1:])))
                print()
        else:  # It's a listing inside an archive
            if self.args['verbose']:
                _fields = ['REPO:', 'PERMS:', 'OWNERSHIP:', 'SIZE:', 'TIMESTAMP:', 'PATH:']
                for r in _results.keys():
                    print('\033[1m{0}\t{1}\033[0m'.format(_fields[0], r))
                    # https://docs.python.org/3/library/string.html#formatspec
                    print('{0[1]:<15}\t{0[2]:<15}\t{0[3]:<15}\t{0[4]:<24}\t{0[5]:<15}'.format(_fields))
                    for line in _results[r]:
                        _fline = line.split()
                        _perms = _fline[0]
                        _ownership = '{0}:{1}'.format(_fline[1], _fline[2])
                        _size = _fline[3]
                        _time = ' '.join(_fline[4:7])
                        _path = ' '.join(_fline[7:])
                        print('{0:<15}\t{1:<15}\t{2:<15}\t{3:<24}\t{4:<15}'.format(_perms,
                                                                                   _ownership,
                                                                                   _size,
                                                                                   _time,
                                                                                   _path))
            else:
                print('\033[1mREPO:\tPATH:\033[0m\n')
                for r in _results.keys():
                    print(r, end = '')
                    for line in _results[r]:
                        _fline = line.split()
                        print('\t{0}'.format(' '.join(_fline[7:])))
        return()

    def lister(self):
        output = {}
        _env = os.environ.copy()
        self.logger.debug('START: lister')
        _env['BORG_RSH'] = self.cfg['config']['ctx']
        for r in self.args['repo']:
            if self.args['archive']:
                _cmd = ['borg',
                        'list',
                        '{0}@{1}:{2}::{3}'.format(self.cfg['config']['user'],
                                                  self.cfg['config']['host'],
                                                  r,
                                                  self.args['archive'])]
            else:
                _cmd = ['borg',
                        'list',
                        '{0}@{1}:{2}'.format(self.cfg['config']['user'],
                                             self.cfg['config']['host'],
                                             r)]
            _env['BORG_PASSPHRASE'] = self.cfg['repos'][r]['password']
            if not self.args['dryrun']:

                _out = subprocess.run(_cmd,
                                       env = _env,
                                       stdout = subprocess.PIPE,
                                       stderr = subprocess.PIPE)
                _stdout = [i.strip() for i in _out.stdout.decode('utf-8').splitlines()]
                _stderr = _out.stderr.decode('utf-8').strip()
                _returncode = _out.returncode
                output[r] = _stdout
                self.logger.debug('[{0}]: (RESULT) {1}'.format(r,
                                                               '\n'.join(_stdout)))
                if _returncode != 0:
                    self.logger.error('[{0}]: STDERR: ({2}) ({1})'.format(r,
                                                                        _stderr,
                                                                        ' '.join(_cmd)))
                if _err != '' and self.cron and _returncode != 0:
                    self.logger.warning('Command {0} failed: {1}'.format(' '.join(cmd), _err)
            del(_env['BORG_PASSPHRASE'])
            if not self.args['archive']:
                if self.args['numlimit'] > 0:
                    if self.args['old']:
                        output[r] = output[r][:self.args['numlimit']]
                    else:
                        output[r] = list(reversed(output[r]))[:self.args['numlimit']]
            if self.args['invert']:
                output[r] = reversed(output[r])
        self.logger.debug('END: lister')
        return(output)

def printMoarHelp():
    _helpstr = ('\n\tNOTE: Sorting only applies to listing archives, NOT the contents!\n\n' +
                'In order to efficiently display results, there are several options to handle it. ' +
                'Namely, these are:\n\n\t\t-s/--sort [direction]\n\t\t-l/--limit [number]\n\t\t-x/--invert\n\n' +
                'For example, if you want to list the 5 most recently *taken* snapshots, you would use:\n\n\t\t-l 5\n\n' +
                'If you would want those SAME results SORTED in the reverse order (i.e. the 5 most recently ' +
                'taken snapshots sorted from newest to oldest), then it would be: \n\n\t\t-l 5 -x\n\n' +
                'Lastly, if you wanted to list the 7 OLDEST TAKEN snapshots in reverse order (that is, ' +
                'sorted from newest to oldest), that\'d be: \n\n\t\t-o -l 7 -x\n')
    print(_helpstr)
    exit(0)

def parseArgs():
    ### DEFAULTS ###
    _date = datetime.datetime.now().strftime("%Y_%m_%d.%H_%M")
    _logfile = '/var/log/borg/{0}'.format(_date)
    _mysqldir = os.path.abspath(os.path.join(os.path.expanduser('~'), 'bak', 'mysql'))
    _stagedir = os.path.abspath(os.path.join(os.path.expanduser('~'), '.bak', 'misc'))
    _cfgfile = os.path.abspath(os.path.join(os.path.expanduser('~'), '.config', 'optools', 'backup.json'))
    _defloglvl = 'info'
    ######
    args = argparse.ArgumentParser(description = 'Backups manager',
                                   epilog = 'TIP: this program has context-specific help. e.g. try "%(prog)s list --help"')
    args.add_argument('-c', '--config',
                      dest = 'cfgfile',
                      default = _cfgfile,
                      help = ('The path to the config file. Default: \033[1m{0}\033[0m'.format(_cfgfile)))
    args.add_argument('-Ll', '--loglevel',
                      dest = 'loglevel',
                      default = _defloglvl,
                      choices = list(loglvls.keys()),
                      help = ('The level of logging to perform. \033[1mWARNING:\033[0m \033[1mdebug\033[0m will log ' +
                              'VERY sensitive information such as passwords! Default: \033[1m{0}\033[0m'.format(_defloglvl)))
    args.add_argument('-Ld', '--log-to-disk',
                      dest = 'disklog',
                      action = 'store_true',
                      help = ('If specified, log to a specific file (-Lf/--logfile)' +
                              ' instead of the system logger.'))
    args.add_argument('-Lf', '--logfile',
                      dest = 'logfile',
                      default = _logfile,
                      help = ('The path to the logfile, only used if -Ld/--log-to-disk ' +
                              'is specified. Default: \033[1m{0}\033[0m (dynamic)').format(_logfile))
    args.add_argument('-v', '--verbose',
                      dest = 'verbose',
                      action = 'store_true',
                      help = ('If specified, log messages will be printed to STDERR ' +
                              'in addition to the other configured log system(s), and verbosity for printing ' +
                              'functions is increased. \033[1mWARNING:\033[0m This may display VERY sensitive information ' +
                              'such as passwords!'))
    ### ARGS FOR ALL OPERATIONS ###
    commonargs = argparse.ArgumentParser(add_help = False)
    commonargs.add_argument('-r', '--repo',
                            dest = 'repo',
                            default = 'all',
                            help = ('The repository to perform the operation for. ' +
                                    'The default is \033[1mall\033[0m, a special value that specifies all known ' +
                                    'repositories. Can also accept a comma-separated list.'))
    remoteargs = argparse.ArgumentParser(add_help = False)
    remoteargs.add_argument('-d', '--dry-run',
                            dest = 'dryrun',
                            action = 'store_true',
                            help = ('Act as if we are performing tasks, but none will actually be executed ' +
                                    '(useful for testing logging)'))
    ### OPERATIONS ###
    subparsers = args.add_subparsers(help = 'Operation to perform',
                                     dest = 'oper')
    backupargs = subparsers.add_parser('backup',
                                       help = 'Perform a backup.',
                                       parents = [commonargs, remoteargs])
    listargs = subparsers.add_parser('list',
                                     help = 'List available backups.',
                                     parents = [commonargs, remoteargs])
    listrepoargs = subparsers.add_parser('listrepos',
                                         help = 'List availabile/configured repositories.',
                                         parents = [commonargs])
    initargs = subparsers.add_parser('init',
                                     help = 'Initialise a repository.',
                                     parents = [commonargs, remoteargs])
    ### OPERATION-SPECIFIC OPTIONS ###
    # CREATE ("backup") #
    backupargs.add_argument('-a',
                            '--archive',
                            default = _date,
                            dest = 'archive',
                            help = ('The name of the archive. Default: \033[1m{0}\033[0m (dynamic)').format(_date))
    backupargs.add_argument('-s',
                            '--stagedir',
                            default = _stagedir,
                            dest = 'stagedir',
                            help = ('The directory used for staging temporary files, ' +
                                    'if necessary. Default: \033[1m{0}\033[0m').format(_stagedir))
    backupargs.add_argument('-m',
                            '--mysqldir',
                            default = _mysqldir,
                            dest = 'mysqldir',
                            help = ('The path to where MySQL dumps should go. ' +
                                    'Default: \033[1m{0}\033[0m').format(_mysqldir))
    # DISPLAY/OUTPUT ("list") #
    listargs.add_argument('-a',
                          '--archive',
                          dest = 'archive',
                          default = False,
                          help = 'If specified, will list the *contents* of the given archive name.')
    listargs.add_argument('-l',
                          '--limit',
                          dest = 'numlimit',
                          type = int,
                          default = '5',
                          help = ('If specified, constrain the outout to this number of ' +
                                  'results each repo. Default is \033[1m5\033[0m, use 0 for unlimited. ' +
                                  'See \033[1m-H/--list-help\033[0m'))
    listargs.add_argument('-s',
                          '--sort',
                          dest = 'sortby',
                          choices = ['newest', 'oldest'],
                          default = 'oldest',
                          help = ('The order to sort the results by. See \033[1m-H/--list-help\033[0m. ' +
                                  'Default: \033[1moldest\033[0m'))
    listargs.add_argument('-x',
                          '--invert',
                          dest = 'invert',
                          action = 'store_true',
                          help = 'Invert the order of results. See \033[1m-H/--list-help\033[0m.')
    listargs.add_argument('-o',
                          '--old',
                          dest = 'old',
                          action = 'store_true',
                          help = ('Instead of grabbing the latest results, grab the earliest results. ' +
                                  'This differs from \033[1m-s/--sort\033[0m. See \033[1m-H/--list-help\033[0m.'))
    listargs.add_argument('-H',
                          '--list-help',
                          dest = 'moarhelp',
                          action = 'store_true',
                          help = 'Print extended information about how to manage the output of listing and exit.')
    return(args)

def main():
    rawargs = parseArgs()
    args = vars(rawargs.parse_args())
    args['cfgfile'] = os.path.abspath(os.path.expanduser(args['cfgfile']))
    if not args['oper']:
        rawargs.print_help()
        exit(0)
    if 'moarhelp' in args.keys() and args['moarhelp']:
        printMoarHelp()
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
    return()
    
if __name__ == '__main__':
    main()
