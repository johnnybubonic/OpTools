#!/usr/bin/env python3

import argparse
import configparser
import copy
import datetime
import os
import pprint
import subprocess
import sys

# TODO: convert .ini to treat [section]s as repositories, with a [DEFAULT]
# section for URL etc.

cfgfile = os.path.join(os.environ['HOME'],
                       '.config',
                       'optools',
                       'repoclone',
                       'arch.ini')

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
    # TODO: this should be a class, probably, instead as there's a lot of shared data across what should be multiple
    # functions.
    with open(os.devnull, 'w') as devnull:
        mntchk = subprocess.run(['findmnt', args['mount']], stdout = devnull, stderr = devnull)
    if mntchk.returncode != 0:
        exit('!! BAILING OUT; {0} isn\'t mounted !!'.format(args['mount']))
    if args['bwlimit'] >= 1:
        opts.insert(10, '--bwlimit=' + str(args['bwlimit']))  # limit socket I/O bandwidth
    for k in ('destination', 'logfile', 'lockfile'):
        os.makedirs(os.path.dirname(args[k]), exist_ok = True)
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
    # end TODO
    # The https://git.server-speed.net/users/flo/bin/tree/syncrepo.sh script uses http(s). to check for lastupdate.
    # I don't, because not all mirrors *have* http(s).
    check_cmd = copy.deepcopy(cmd)
    check_cmd.append(os.path.join(args['mirror'], 'lastupdate'))
    check_cmd.append(os.path.join(args['destination'], 'lastupdate'))
    update_cmd = copy.deepcopy(cmd)
    update_cmd.append(os.path.join(args['mirror'], 'lastsync'))
    update_cmd.append(os.path.join(args['destination'], 'lastsync'))
    cmd.append(os.path.join(args['mirror'], '.'))  # the path on the remote mirror (full sync)
    cmd.append(os.path.join(args['destination'], '.'))  # the local destination (full sync)
    if os.path.isfile(args['lockfile']):
        with open(args['lockfile'], 'r') as f:
            existingpid = f.read().strip()
        if os.isatty(sys.stdin.fileno()):
            # Running from shell
            exit('!! A repo synchronization seems to already be running (PID: {0}). Quitting. !!'.format(existingpid))
        else:
            exit()  # we're running in cron, shut the hell up.
    else:
        with open(args['lockfile'], 'w') as f:
            f.write(str(os.getpid()))
    # determine if we need to do a full sync.
    # TODO: clean this up. there's a lot of code duplication here, and it should really be a function.
    with open(os.path.join(args['destination'], 'lastupdate'), 'r') as f:
        oldupdate = datetime.datetime.utcfromtimestamp(int(f.read().strip()))
    with open(os.devnull, 'wb') as devnull:
        # TODO: when i clean this up, change this to do error detection
        c = subprocess.run(check_cmd, stdout = devnull, stderr = devnull)
        c2 = subprocess.run(update_cmd, stdout = devnull, stderr = devnull)
    with open(os.path.join(args['destination'], 'lastupdate'), 'r') as f:
        newupdate = datetime.datetime.utcfromtimestamp(int(f.read().strip()))
    if newupdate > oldupdate:
        with open(args['logfile'], 'a') as log:
            c = subprocess.run(cmd, stdout = log, stderr = subprocess.PIPE)
        now = int(datetime.datetime.timestamp(datetime.datetime.utcnow()))
        with open(os.path.join(args['destination'], 'lastsync'), 'w') as f:
            f.write(str(now) + '\n')
    else:
        # No-op. Stderr should be empty.
        c = subprocess.run(['echo'], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        now = int(datetime.datetime.timestamp(datetime.datetime.utcnow()))
    with open(args['lastcheck'], 'w') as f:
        f.write(str(now) + '\n')
    os.remove(args['lockfile'])
    # Only report errors at the end of the run if we aren't running in cron. Otherwise, log them.
    errors = c.stderr.decode('utf-8').splitlines()
    if os.isatty(sys.stdin.fileno()) and errors:
        print('We encountered some errors:')
        for e in errors:
            if e.startswith('symlink has no referent: '):
                print('Broken upstream symlink: {0}'.format(e.split()[1].replace('"', '')))
            else:
                print(e)
    elif errors:
        with open(args['logfile'], 'a') as f:
            for e in errors:
                f.write('{0}\n'.format(e))
    return()

def getDefaults():
    # Hardcoded defaults
    dflt = {'mirror': 'rsync://mirror.square-r00t.net/arch/',
            'repos': 'core,extra,community,multilib,iso/latest',
            'destination': '/srv/repos/arch',
            'lastcheck': '/srv/http/arch.lastcheck',
            'mount': '/',
            'bwlimit': 0,
            'lockfile': '/var/run/repo-sync_arch.lck',
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
                                            'if one is not found.').format(cfgfile))
    args.add_argument('-m',
                      '--mirror',
                      dest = 'mirror',
                      default = liveopts['mirror'],
                      help = ('The upstream mirror to sync from, must be an rsync URI '+
                              '(Default: {0}').format(liveopts['mirror']))
# TODO: can we do this?
# We can; we need to .format() a repo in, probably, on the src and dest.
# Problem is the last updated/last synced files.
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
    args.add_argument('-c', '--last-check',
                      dest = 'lastcheck',
                      default = liveopts['lastcheck'],
                      help = ('The file to update with a timestamp on every run. Per spec, this must be outside the '
                              'repository webroot'))
    args.add_argument('-b',
                      '--bwlimit',
                      dest = 'bwlimit',
                      default = liveopts['bwlimit'],
                      type = int,
                      help = ('The amount, in Kilobytes per second, to throttle the sync to. Default is to not '
                              'throttle (0).'))
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
    return()

if __name__ == '__main__':
    main()
