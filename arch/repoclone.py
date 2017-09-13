#!/usr/bin/env python3

import argparse
import datetime
import os
import subprocess

mirror = 'rsync://mirror.wdc1.us.leaseweb.net/archlinux'  # must be an rsync mirror; base path
dest = {'mount':'/mnt/raidbox', 'path':'/mnt/raidbox/repos/arch'}
bwlimit = 7000  # in Kilobyte/s by default; set to 0 to disable bandwidth throttling
# currently not used:
repos = ['core',
         'extra',
         'community',
         'multilib',
         'iso/latest']
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

if bwlimit >= 1:
    opts.insert(10, '--bwlimit=' + str(bwlimit))  # limit socket I/O bandwidth

lockfile = '/var/run/repo-sync.lck'
logfile = '/var/log/repo/arch.log'

def sync():
    # TODO: safer file creation etc. - make sure parent dirs exist.
    # TODO: check that destination is mounted first.
    paths = os.environ['PATH'].split(':')
    rsync = '/usr/bin/'  # set the default
    for p in paths:
        testpath = os.path.join(p, 'rsync')
        if os.path.isfile(testpath):
            rsync = testpath  # in case rsync isn't in /usr/bin/rsync
            break
    cmd = [rsync]  # the path to the binary
    cmd.extend(opts)  # the arguments
    cmd.append(os.path.join(mirror, '.'))  # the path on the remote mirror
    cmd.append(os.path.join(dest['path'], '.'))  # the local destination
    if os.path.isfile(lockfile):
        with open(lockfile, 'r') as f:
            existingpid = f.read().strip()
        exit('!! A repo synchronization seems to already be running (PID: {0}). Quitting. !!'.format(existingpid))
    else:
        with open(lockfile, 'w') as f:
            f.write(str(os.getpid()))
    with open(logfile, 'a') as log:
        try:
            subprocess.call(cmd, stdout = log, stderr = subprocess.STDOUT)
            now = int(datetime.datetime.timestamp(datetime.datetime.utcnow()))
            with open(os.path.join(dest['path'], 'lastsync'), 'w') as f:
                f.write(str(now) + '\n')
            os.remove(lockfile)
        except:
            os.remove(lockfile)
            exit('!! The rsync has failed. See {0} for more details. !!'.format(logfile))
    return()

def parseArgs():
    pass  # TODO: make this moar configurable

def main():
    sync()

if __name__ == '__main__':
    main()
