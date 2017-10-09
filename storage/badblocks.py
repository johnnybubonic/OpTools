#!/usr/bin/env python3

# Email alerts about disks if there are any errors found.
# It can take a LONG time depending on the speed/type of disk and size of disk.
# Should probably only cron it once a week or so.

import os
import subprocess

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
    pass

def main():
    pass

def userChk():
    # Needs to be run as root/with sudo, because of e.g. cryptsetup, etc.
    if os.geteuid() != 0:
        raise PermissionError('This script must be run with root privileges.')

if __name__ == '__main__':
    main()
