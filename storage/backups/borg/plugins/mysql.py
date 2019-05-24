import copy
import os
import re
import subprocess
import warnings

_mysql_ssl_re = re.compile('^ssl-(.*)$')

# TODO: is it possible to do a pure-python dump via PyMySQL?

class Backup(object):
    def __init__(self, dbs = None,
                       cfg = '~/.my.cnf',
                       cfgsuffix = '',
                       splitdumps = True,
                       dumpopts = None,
                       mysqlbin = 'mysql',
                       mysqldumpbin = 'mysqldump',
                       outdir = '~/.cache/backup/mysql'):
        # If dbs is None, we dump ALL databases.
        self.dbs = dbs
        self.cfgsuffix = cfgsuffix
        self.splitdumps = splitdumps
        self.mysqlbin = mysqlbin
        self.mysqldumpbin = mysqldumpbin
        self.outdir = os.path.abspath(os.path.expanduser(outdir))
        self.cfg = os.path.abspath(os.path.expanduser(cfg))
        os.makedirs(self.outdir, exist_ok = True)
        os.chmod(self.outdir, mode = 0o0700)
        if not os.path.isfile(self.cfg):
            raise OSError(('{0} does not exist!').format(self.cfg))
        if not dumpopts:
            self.dumpopts = ['--routines',
                             '--add-drop-database',
                             '--add-drop-table',
                             '--allow-keywords',
                             '--complete-insert',
                             '--create-options',
                             '--extended-insert']
        else:
            self.dumpopts = dumpopts
        self.getDBs()
        self.dump()

    def getDBs(self):
        if not self.dbs:
            _out = subprocess.run([self.mysqlbin, '-BNne', 'SHOW DATABASES'],
                                  stdout = subprocess.PIPE,
                                  stderr = subprocess.PIPE)
            if _out.returncode != 0:
                raise RuntimeError(('Could not successfully list databases: '
                                    '{0}').format(_out.stderr.decode('utf-8')))
            self.dbs = _out.stdout.decode('utf-8').strip().splitlines()
        return()

    def dump(self):
        for db in self.dbs:
            args = copy.deepcopy(self.dumpopts)
            outfile = os.path.join(self.outdir, '{0}.sql'.format(db))
            if db in ('information_schema', 'performance_schema'):
                args.append('--skip-lock-tables')
            elif db == 'mysql':
                args.append('--flush-privileges')
            out = subprocess.run([self.mysqldumpbin,
                                  '--result-file={0}'.format(outfile),
                                  args,
                                  db],
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.PIPE)
            if out.returncode != 0:
                warn = ('Error dumping {0}: {1}').format(db, out.stderr.decode('utf-8').strip())
                warnings.warn(warn)
        return()
