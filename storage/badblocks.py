#!/usr/bin/env python3

# Email alerts about disks if there are any errors found.
# It can take a LONG time depending on the speed/type of disk and size of disk.
# Should probably only cron it once a week or so.

import os
import pycryptsetup  # requires cryptsetup to be configured with '--enable-python --with-python_version=3.6' (or whatever your python version is)
import lvm  # requires lvm2 to be configured with '-enable-python3_bindings'
import subprocess

def getDisks():
    disks = []
    for d in psutil.disk_partitions(all = False):
        if d.device not in disks:  # Avoid dupes
            _devpath = os.path.split(d.device)
            if _devpath[1] == 'mapper':  # It's actually an LVM, LUKS, etc.
                # Is it an LVM device?
                if lvm.scan():
                    continue
                # Is it a LUKS device?
                _crypt = pycryptsetup.CryptSetup(d.device)
                if _crypt.isLuks() == 0:
                    # We can (and should) get the actual physical device
                    _dev = _crypt.info()['device']
                    if _dev not in disks:
                        disks.append(_dev)
            else:
                disks.append(d.device)
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
