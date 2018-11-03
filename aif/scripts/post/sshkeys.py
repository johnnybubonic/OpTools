#!/usr/bin/env python3

import os
import pwd
from urllib.request import urlopen

keysfile = 'https://square-r00t.net/ssh/all'

def copyKeys(keystring, user = 'root'):
    uid = pwd.getpwnam(user).pw_uid
    gid = pwd.getpwnam(user).pw_gid
    homedir = os.path.expanduser('~{0}'.format(user))
    sshdir = '{0}/.ssh'.format(homedir)
    authfile = '{0}/authorized_keys'.format(sshdir)
    os.makedirs(sshdir, mode = 0o700, exist_ok = True)
    with open(authfile, 'a') as f:
        f.write(keystring)
    for basedir, dirs, files in os.walk(sshdir):
        os.chown(basedir, uid, gid)
        os.chmod(basedir, 0o700)
        for f in files:
            os.chown(os.path.join(basedir, f), uid, gid)
            os.chmod(os.path.join(basedir, f), 0o600)
    return()

def main():
    with urlopen(keysfile) as keys:
        copyKeys(keys.read().decode('utf-8'))

if __name__ == '__main__':
    main()
