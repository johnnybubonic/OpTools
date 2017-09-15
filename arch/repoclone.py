#!/usr/bin/env python3

import argparse
import configparser
import datetime
import os
import pprint
import subprocess

cfgfile = os.path.join(os.environ['HOME'], '.arch.repoclone.ini')

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
        '--exclude=.*'  # exclude files matching PATTERN
       ]

def sync(args):
    with open(os.devnull, 'w') as devnull:
        mntchk = subprocess.run(['findmnt', args['mount']], stdout = devnull, stderr = devnull)
    if mntchk.returncode != 0:
        exit('!! BAILING OUT; {0} isn\'t mounted !!'.format(args['mount']))
    if args['bwlimit'] >= 1:
        opts.insert(10, '--bwlimit=' + str(args['bwlimit']))  # limit socket I/O bandwidth
    for k in ('destination', 'logfile', 'lockfile'):
        os.makedirs(args[k], exist_ok = True)
    paths = os.environ['PATH'].split(':')
    rsync = '/usr/bin/rsync'  # set the default
    for p in paths:
        testpath = os.path.join(p, 'rsync')
        if os.path.isfile(testpath):
            rsync = testpath  # in case rsync isn't in /usr/bin/rsync
            break
    cmd = [rsync]  # the path to the binary
    cmd.extend(opts)  # the arguments
    # TODO: implement repos here?
    cmd.append(os.path.join(args['mirror'], '.'))  # the path on the remote mirror
    cmd.append(os.path.join(args['destination'], '.'))  # the local destination
    if os.path.isfile(args['lockfile']):
        with open(args['lockfile'], 'r') as f:
            existingpid = f.read().strip()
        exit('!! A repo synchronization seems to already be running (PID: {0}). Quitting. !!'.format(existingpid))
    else:
        with open(args['lockfile'], 'w') as f:
            f.write(str(os.getpid()))
    with open(args['logfile'], 'a') as log:
        try:
            subprocess.call(cmd, stdout = log, stderr = subprocess.STDOUT)
            now = int(datetime.datetime.timestamp(datetime.datetime.utcnow()))
            with open(os.path.join(dest['path'], 'lastsync'), 'w') as f:
                f.write(str(now) + '\n')
            os.remove(args['lockfile'])
        except:
            os.remove(args['lockfile'])
            exit('!! The rsync has failed. See {0} for more details. !!'.format(args['logfile']))
    return()

def getDefaults():
    # Hardcoded defaults
    dflt = {'mirror': 'rsync://mirror.square-r00t.net/arch/',
            'repos': 'core,extra,community,multilib,iso/latest',
            'destination': '/srv/repos/arch',
            'mount': '/',
            'bwlimit': 0,
            'lockfile': '/var/run/repo-sync.lck',
            'logfile': '/var/log/repo/arch.log'}
    realcfg = configparser.ConfigParser(defaults = dflt)
    if not os.path.isfile(cfgfile):
        with open(cfgfile, 'w') as f:
            realcfg.write(f)
    realcfg.read(cfgfile)
    return(realcfg)

def parseArgs():
    cfg = getDefaults()
    liveopts = cfg['DEFAULT']
    args = argparse.ArgumentParser(description = 'Synchronization for a remote Arch repository to a local one.',
                                   epilog = ('This program will write a default configuration file to {0} ' +
                                            'if one is not found.'.format(cfgfile)))
    args.add_argument('-m',
                      '--mirror',
                      dest = 'mirror',
                      default = liveopts['mirror'],
                      help = ('The upstream mirror to sync from, must be an rsync URI '+
                              '(Default: {0}').format(liveopts['mirror']))
# TODO: can we do this?
#    args.add_argument('-r',
#                      '--repos',
#                      dest = 'repos',
#                      default = liveopts['repos'],
#                      help = ('The repositories to sync; must be a comma-separated list. ' +
#                              '(Currently not used.) Default: {0}').format(','.join(liveopts['repos'])))
    args.add_argument('-d',
                      '--destination',
                      dest = 'destination',
                      default = liveopts['destination'],
                      help = 'The destination directory to sync to. Default: {0}'.format(liveopts['destination']))
    args.add_argument('-b',
                      '--bwlimit',
                      dest = 'bwlimit',
                      default = liveopts['bwlimit'],
                      type = int,
                      help = 'The amount, in Kilobytes per second, to throttle the sync to. Default is to not throttle (0).')
    args.add_argument('-l',
                      '--log',
                      dest = 'logfile',
                      default = liveopts['logfile'],
                      help = 'The path to the logfile. Default: {0}'.format(liveopts['logfile']))
    args.add_argument('-L',
                      '--lock',
                      dest = 'lockfile',
                      default = liveopts['lockfile'],
                      help = 'The path to the lockfile. Default: {0}'.format(liveopts['lockfile']))
    args.add_argument('-M',
                      '--mount',
                      dest = 'mount',
                      default = liveopts['mount'],
                      help = 'The mountpoint for your --destination. The script will exit if this point is not mounted. ' +
                             'If you don\'t need mount checking, just use /. Default: {0}'.format(liveopts['mount']))
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    sync(args)

if __name__ == '__main__':
    main()
