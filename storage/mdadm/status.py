#!/usr/bin/env python3

import mdstat  # apacman -S python-mdstat
import os
import subprocess

# also requires parted to be installed

def getMdstat():
    mds = {}
    with open(os.devnull, 'w') as DEVNULL:
        _devlines = subprocess.run(['mdadm',
                                    '--detail',
                                    '--scan'],
                                   stderr = DEVNULL,
                                   stdout = subprocess.PIPE).stdout.decode('utf-8')
    for m in _devlines.split():
        l = m.split()
        dev = os.path.split(l[1])[-1]
        mds[dev] = {'device': l[1].strip(),
                    'metadata': l[2].split('=')[1].strip(),
                    'host': l[3].split('=')[1].split(':')[0].strip(),
                    'name': l[3].split('=')[1].split(':')[1].strip(),
                    'uuid': l[4].split('=')[1].strip()}
        _md = mdstat.parse()['devices'][dev]
        mds[dev]['status'] = ('active' if _md['active'] else 'inactive')
        mds[dev]['members'] = _md['disks']
        if _md['resync']:
            mds[dev]['status'] = _md['resync']
        # TODO: I STOPPED HERE

def userChk():
    # Needs to be run as root/with sudo, because we need to use mdadm --detail --scan etc.
    if os.geteuid() != 0:
        raise PermissionError('This script must be run with root privileges.')

def main():
    userChk()
    getMdstat()

if __name__ == '__main__':
    main()