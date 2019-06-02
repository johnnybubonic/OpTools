import copy
import os
import re
import subprocess
import warnings

_mysql_ssl_re = re.compile('^ssl-(.*)$')

# TODO: is it possible to do a pure-python dump via PyMySQL?
# TODO: add compression support? Not *that* necessary since borg has its own.
#       in fact, it's better to not do it on the dumps directly so borg can diff/delta better.

class Backup(object):
    def __init__(self, dbs = None,
                       cfg = '~/.my.cnf',
                       cfgsuffix = '',
                       splitdumps = True,
                       dumpopts = None,
                       mysqlbin = 'mysql',
                       mysqldumpbin = 'mysqldump',
                       outdir = '~/.cache/backup/mysql'):
        # If dbs is None, we dump ALL databases (that the user has access to).
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
        if self.splitdumps:
            for db in self.dbs:
                args = copy.deepcopy(self.dumpopts)
                outfile = os.path.join(self.outdir, '{0}.sql'.format(db))
                if db in ('information_schema', 'performance_schema'):
                    args.append('--skip-lock-tables')
                elif db == 'mysql':
                    args.append('--flush-privileges')
                cmd = [self.mysqldumpbin,
                       '--result-file={0}'.format(outfile)]
                cmd.extend(args)
                cmd.append(db)
                out = subprocess.run(cmd,
                                     stdout = subprocess.PIPE,
                                     stderr = subprocess.PIPE)
                if out.returncode != 0:
                    warn = ('Error dumping {0}: {1}').format(db, out.stderr.decode('utf-8').strip())
                    warnings.warn(warn)
        else:
            outfile = os.path.join(self.outdir, 'all.databases.sql')
            args = copy.deepcopy(self.dumpopts)
            args.append('--result-file={0}'.format(outfile))
            if 'information_schema' in self.dbs:
                args.append('--skip-lock-tables')
            if 'mysql' in self.dbs:
                args.append('--flush-privileges')
            args.append(['--databases'])
            cmd = [self.mysqldumpbin]
            cmd.extend(args)
            cmd.extend(self.dbs)
            out = subprocess.run(cmd,
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.PIPE)
            if out.returncode != 0:
                warn = ('Error dumping {0}: {1}').format(','.join(self.dbs),
                                                         out.stderr.decode('utf-8').strip())
                warnings.warn(warn)
        return()
