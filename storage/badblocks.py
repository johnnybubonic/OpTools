#!/usr/bin/env python3

# Email alerts about disks if there are any errors found.
# It can take a LONG time depending on the speed/type of disk and size of disk.
# Should probably only cron it once a week or so.

import datetime
import os
import subprocess
import sys

# needs badblocks, smartctl, and parted installed also

def getDisks():
    disks = []
    with open(os.devnull, 'w') as _DEVNULL:
        _rawlist = subprocess.run(['parted',
                                   '--list',
                                   '--machine',
                                   '--script'],
                                  stdout = subprocess.PIPE,
                                  stderr = _DEVNULL).stdout.decode('utf-8')
    for l in _rawlist.splitlines():
        if l in ('', 'BYT;'):
            continue  # Skip empty lines and markers for new devices
        elif l.startswith('/'):
            # It's a device path.
            _l = l.split(':')
            if _l[2] not in ('md', 'dm'):  # Skip non-block devices like MDADM arrays, LVM volumes
                if _l[0] not in disks:
                    disks.append(_l[0])
    return(disks)

def chkDisk(disk):
    d = '.'.join(os.path.split(disk)[1:])
    os.makedirs('/var/log/badblocks', exist_ok = True)
    if os.path.isfile('/var/log/badblocks/{0}.log'.format(d)):
        # for some reason this file was just created within the past 24 hours,
        # so we better play it safe and write to a different log file
        now = datetime.datetime.now()
        modified = datetime.datetime.fromtimestamp(os.path.getmtime('/var/log/badblocks/{0}.log'.format(d)))
        diff = now - modified
        timedelta = datetime.timedelta(days = 1)
        if not diff >= timedelta:
            d += '_secondary'
    bb = ['badblocks',
          '-o', '/var/log/badblocks/{0}.log'.format(d),
          disk]
    smctl = ['smartctl',
             '-t', 'long',
             '-d', 'sat',
             disk]
    with open(os.devnull, 'w') as DEVNULL:
        for c in (bb, smctl):
            subprocess.run(c, stdout = DEVNULL)
    return()

def userChk():
    # Needs to be run as root/with sudo, because of e.g. cryptsetup, etc.
    if os.geteuid() != 0:
        raise PermissionError('This script must be run with root privileges.')

def main():
    userChk()
    for d in getDisks():
        chkDisk(d)

if __name__ == '__main__':
    main()
