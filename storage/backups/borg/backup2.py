#!/usr/bin/env python3

# TODO: https://borgbackup.readthedocs.io/en/latest/internals/frontends.html
# will they EVER release a public API? for now we'll just use subprocess since
# we import it for various prep stuff anyways.

import argparse
import configparser
import datetime
import json
import logging
import os
import subprocess
import sys
try:
    import pymysql  # not stdlib; "python-pymysql" in Arch's AUR
    has_mysql = True
except ImportError:
    has_mysql = False

### LOG LEVEL MAPPINGS ###
loglvls = {'critical': logging.CRITICAL,
           'error': logging.ERROR,
           'warning': logging.WARNING,
           'info': logging.INFO,
           'debug': logging.DEBUG}

class Backup(object):
    def __init__(self, args):
        self.args = args
        # Set up logging
        logging.basicConfig(level = self.args['loglevel'])
        logger = logging.getLogger(__name__)
        pass

def parseArgs():
    ### DEFAULTS ###
    _date = datetime.datetime.now().strftime("%Y_%m_%d.%H_%M")
    _logfile = '/var/log/borg/{0}'.format(_date)
    _mysqldir = os.path.abspath(os.path.join(os.path.expanduser('~'), 'bak', 'mysql'))
    _stagedir = '/root/bak/misc'
    _cfgfile = os.path.abspath(os.path.join(os.path.expanduser('~')),
                                            '.backcfg.json')
    _defloglvl = 'info'
    ######
    args = argparse.ArgumentParser(description = 'Backups manager',
                                   epilog = 'TIP: this program has context-specific help. e.g. try "%(prog)s list --help"')
    commonargs = argparse.ArgumentParser(add_help = False)
    commonargs.add_argument('-r',
                            '--repo',
                            dest = 'repo',
                            help = ('The repository to perform the operation for. ' +
                                    'The default is \'all\', a special value that specifies all known ' +
                                    'repositories. Can also accept a comma-separated list.'),
                            default = 'all')
    commonargs.add_argument('-L',
                            '--loglevel',
                            dest = 'loglevel',
                            default = _defloglvl,
                            choices = list(loglvls.keys()),
                            help = 'The level of logging to perform. Default: {0}'.format(_defloglvl))
    commonargs.add_argument('-Ld',
                            '--log-to-disk',
                            dest = 'disklog',
                            action = 'store_true',
                            help = ('If specified, log to a specific file (-Lf/--logfile)' +
                                    ' instead of the system logger.'))
    commonargs.add_argument('-Lf',
                            '--logfile',
                            dest = 'logfile',
                            default = _logfile,
                            help = ('The path to the logfile, only used if -Ld/--log-to-disk ' +
                                    'is specified. Default: {0} (dynamic)').format(_logfile))
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
    backupargs.add_argument('-a',
                            '--archive',
                            default = _date,
                            dest = 'archive',
                            help = ('The name of the archive. Default: {0} (dynamic)').format(_date))
    backupargs.add_argument('-s',
                            '--stagedir',
                            default = _stagedir,
                            dest = 'stagedir',
                            help = ('The directory used for staging temporary files, ' +
                                    'if necessary. Default: {0}').format(_stagedir))
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
                                  'results each repo. Default is 5, 0 for unlimited. See -H/--list-help.'))
    listargs.add_argument('-s',
                          '--sort',
                          dest = 'sortby',
                          choices = ['newest', 'oldest'],
                          default = 'oldest',
                          help = 'The order to sort the results by. See -H/--list-help.')
    listargs.add_argument('-x',
                          '--invert',
                          dest = 'invert',
                          action = 'store_true',
                          help = 'Invert the order of *results*. See -H/--list-help.')
    listargs.add_argument('-o',
                          '--old',
                          dest = 'old',
                          action = 'store_true',
                          help = ('Instead of grabbing the latest results, grab the earliest results. ' +
                                  'This differs from -s/--sort. See -H/--list-help.'))
    listargs.add_argument('-H',
                          '--list-help',
                          dest = 'moarhelp',
                          action = 'store_true',
                          help = 'Print extended information about how to manage the output of listing and exit.')
    listargs.add_argument('-v',
                          '--verbose',
                          dest = 'verbose',
                          help = ('Print out detailed information for archive contents ' +
                                  '(only valid if -a is set). WARNING: May include sensitive data.'),
                          action = 'store_true')
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    
if __name__ == '__main__':
    main()