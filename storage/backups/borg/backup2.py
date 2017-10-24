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
            handlers.append(logging.handlers.RotatingFileHandler(self.args['logfile'],
                                                                 encoding = 'utf8',
                                                                 maxBytes = 100000,
                                                                 backupCount = 1))
        if self.args['verbose']:
            handlers.append(logging.StreamHandler())
        if has_systemd:
            handlers.append(journal.JournalHandler())
        for h in handlers:
            h.setFormatter(_logfmt)
            h.setLevel(loglvls[self.args['loglevel']])
            self.logger.addHandler(h)
        ### CONFIG ###
        if not os.path.isfile(self.args['cfgfile']):
            self.logger.error('{0} does not exist'.format(self.args['cfgfile']))
            exit(1)

        def create(self):
            pass

        def miscBak(self, pkgr):
            pass

        def mysqlBak(self):
            pass

        def listRepos(self):
            pass

        def printer(self):
            pass

        def lister(self):
            pass

def printMoarHelp():
    helpstr = ('\n\tNOTE: Sorting only applies to listing archives, NOT the contents!\n\n' +
    'In order to efficiently display results, there are several options to handle it. ' +
    'Namely, these are:\n\n\t\t-s/--sort [direction]\n\t\t-l/--limit [number]\n\t\t-x/--invert\n\n' +
    'For example, if you want to list the 5 most recently *taken* snapshots, you would use:\n\n\t\t-l 5\n\n' +
    'If you would want those SAME results SORTED in the reverse order (i.e. the 5 most recently ' +
    'taken snapshots sorted from newest to oldest), then it would be: \n\n\t\t-l 5 -x\n\n' +
    'Lastly, if you wanted to list the 7 OLDEST TAKEN snapshots in reverse order (that is, ' +
    'sorted from newest to oldest), that\'d be: \n\n\t\t-o -l 7 -x\n')
    print(helpstr)
    exit(0)

def parseArgs():
    ### DEFAULTS ###
    _date = datetime.datetime.now().strftime("%Y_%m_%d.%H_%M")
    _logfile = '/var/log/borg/{0}'.format(_date)
    _mysqldir = os.path.abspath(os.path.join(os.path.expanduser('~'), 'bak', 'mysql'))
    _stagedir = '/root/bak/misc'
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
                      help = 'The level of logging to perform. Default: \033[1m{0}\033[0m'.format(_defloglvl))
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
                      help = ('If specified, log messages will be printed to STDOUT/STDERR ' +
                              'in addition to the other configured log systems.'))
    ### ARGS FOR ALL OPERATIONS ###
    commonargs = argparse.ArgumentParser(add_help = False)
    commonargs.add_argument('-r', '--repo',
                            dest = 'repo',
                            default = 'all',
                            help = ('The repository to perform the operation for. ' +
                                    'The default is \033[1mall\033[0m, a special value that specifies all known ' +
                                    'repositories. Can also accept a comma-separated list.'))
    ### OPERATIONS ###
    subparsers = args.add_subparsers(help = 'Operation to perform',
                                     dest = 'oper')
    backupargs = subparsers.add_parser('backup',
                                       help = 'Perform a backup.',
                                       parents = [commonargs])
    listargs = subparsers.add_parser('list',
                                     help = 'List available backups.',
                                     parents = [commonargs])
    listrepoargs = subparsers.add_parser('listrepos',
                                         help = 'List availabile/configured repositories.',
                                         parents = [commonargs])
    initargs = subparsers.add_parser('init',
                                     help = 'Initialise a repository.',
                                     parents = [commonargs])
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
    # DISPLAY/OUTPUT ("list") #
    listargs.add_argument('-a',
                          '--archive',
                          dest = 'archive',
                          default = False,
                          help = 'If specified, will list the *contents* of a certain archive.')
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
    import pprint  # DEBUG
    pprint.pprint(args)  # DEBUG
    if not args['oper']:
        rawargs.print_help()
        exit(0)
    if 'moarhelp' in args.keys() and args['moarhelp']:
        printMoarHelp()
    bak = Backup(args)
    
if __name__ == '__main__':
    main()
