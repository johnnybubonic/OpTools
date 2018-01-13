#!/usr/bin/env python3

import datetime
import os
import re
import shutil
import subprocess
from urllib.request import urlopen

pkg_base = 'apacman'
pkgs = ('', '-deps', '-utils')
url_base = 'https://aif.square-r00t.net/cfgs/files'
local_dir = '/tmp'

conf_options = {}
conf_options['apacman'] = {'enabled': ['needed', 'noconfirm', 'noedit', 'progress', 'purgebuild', 'skipcache', 'keepkeys'],
                           'disabled': [],
                           'values': {'tmpdir': '"/var/tmp/apacmantmp-$UID"'}}
conf_options['pacman'] = {'enabled': [],
                          'disabled': [],
                          'values': {'UseSyslog': None, 'Color': None, 'TotalDownload': None, 'CheckSpace': None, 'VerbosePkgLists': None}}

def downloadPkg(pkgfile, dlfile):
    url = os.path.join(url_base, pkgfile)
    # Prep the destination
    os.makedirs(os.path.dirname(dlfile), exist_ok = True)
    # Download the pacman package
    with urlopen(url) as u:
        with open(dlfile, 'wb') as f:
            f.write(u.read())
    return()

def installPkg(pkgfile):
    # Install it
    subprocess.run(['pacman', '-Syyu'])  # Installing from an inconsistent state is bad, mmkay?
    subprocess.run(['pacman', '--noconfirm', '--needed', '-S', 'base-devel'])
    subprocess.run(['pacman', '--noconfirm', '--needed', '-S', 'multilib-devel'])
    subprocess.run(['pacman', '--noconfirm', '--needed', '-U', pkgfile])
    return()

def configurePkg(opts, pkgr):
    cf = '/etc/{0}.conf'.format(pkgr)
    # Configure it
    shutil.copy2(cf, '{0}.bak.{1}'.format(cf, int(datetime.datetime.utcnow().timestamp())))
    with open(cf, 'r') as f:
        conf = f.readlines()
    for idx, line in enumerate(conf):
        l = line.split('=')
        opt = l[0].strip('\n').strip()
        if len(l) > 1:
            val = l[1].strip('\n').strip()
        # enabled options
        for o in opts['enabled']:
            if re.sub('^#?', '', opt).strip() == o:
                if pkgr == 'apacman':
                    conf[idx] = '{0}=1\n'.format(o)
                elif pkgr == 'pacman':
                    conf[idx] = '{0}\n'.format(o)
        # disabled options
        for o in opts['disabled']:
            if re.sub('^#?', '', opt).strip() == o:
                if pkgr == 'apacman':
                    conf[idx] = '{0}=0\n'.format(o)
                elif pkgr == 'pacman':
                    conf[idx] = '#{0}\n'.format(o)
        # values
        for o in opts['values']:
            if opts['values'][o] is not None:
                if re.sub('^#?', '', opt).strip() == o:
                    if pkgr == 'apacman':
                        conf[idx] = '{0}={1}\n'.format(o, opts['values'][o])
                    elif pkgr == 'pacman':
                        conf[idx] = '{0} = {1}\n'.format(o, opts['values'][o])
            else:
                if re.sub('^#?', '', opt).strip() == o:
                    conf[idx] = '{0}\n'.format(o)
    with open(cf, 'w') as f:
        f.write(''.join(conf))

def finishPkg():
    # Finish installing (optional deps)
    for p in ('git', 'customizepkg-scripting', 'pkgfile', 'rsync'):
        subprocess.run(['apacman', '--noconfirm', '--needed', '-S', p])

def main():
    for p in pkgs:
        pkg = pkg_base + p
        fname = '{0}.tar.xz'.format(pkg)
        local_pkg = os.path.join(local_dir, fname)
        downloadPkg(fname, local_pkg)
        installPkg(local_pkg)
    for tool in ('pacman', 'apacman'):
        configurePkg(conf_options[tool], tool)
    finishPkg()
    return()

if __name__ == '__main__':
    main()
