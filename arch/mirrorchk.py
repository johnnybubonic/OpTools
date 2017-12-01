#!/usr/bin/env python3

import os
import re
import subprocess
import tempfile
from urllib.request import urlopen

# The local list of mirrors
mfile = '/etc/pacman.d/mirrorlist'
# The URL for the list of mirros
# TODO: customize with country in a config
rlist = 'https://www.archlinux.org/mirrorlist/?country=US&protocol=http&protocol=https&ip_version=4&use_mirror_status=on'
# If local_mirror is set to None, don't do any modifications.
# If it's a dict in the format of:
#   local_mirror = {'profile': 'PROFILE_NAME',
#                   'url': 'http://host/arch/%os/$arch',
#                   'state_file': '/var/lib/netctl/netctl.state'}
# Then we will check 'state_file'. If its contents match 'profile',
# then we will add 'url' to the *top* of mfile.
# TODO: I need to move this to a config.
local_mirror = {'profile': '<PROFILENAME>',
                'url': 'http://<REPOBOX>/arch/$repo/os/$arch',
                'state_file': '/var/lib/netctl/netctl.state'}

def getList(url):
    with urlopen(url) as http:
        l = http.read().decode('utf-8')
    return(l)

def uncomment(url_list):
    urls = []
    if isinstance(url_list, str):
        url_list = [u.strip() for u in url_list.splitlines()]
    for u in url_list:
        u = u.strip()
        if u == '':
            continue
        urls.append(re.sub('^\s*#', '', u))
    return(urls)

def rankList(mfile):
    c = ['rankmirrors',
         '-n', '6',
         mfile]
    ranked_urls = subprocess.run(c, stdout = subprocess.PIPE)
    url_list = ranked_urls.stdout.decode('utf-8').splitlines()
    for u in url_list[:]:
        if u.strip() == '':
            url_list.remove(u)
            continue
        if re.match('^\s*(#.*)$', u, re.MULTILINE | re.DOTALL):
            url_list.remove(u)
    return(url_list)

def localMirror(url_list):
    # If checking the state_file doesn't work out, use netctl
    # directly.
    if not isinstance(local_mirror, dict):
        return(url_list)
    with open(local_mirror['state_file'], 'r') as f:
        state = f.read().strip()
    state = [s.strip() for s in state]
    if local_mirror['profile'] in state:
        url_list.insert(0, 'Server = {0}'.format(local_mirror['url']))
    return(url_list)

def writeList(mirrorfile, url_list):
    with open(mirrorfile, 'w') as f:
        f.write('{0}\n'.format('\n'.join(url_list)))
    return()

if __name__ == '__main__':
    if os.geteuid() != 0:
        exit('Must be run as root.')
    urls = getList(rlist)
    t = tempfile.mkstemp(text = True)
    writeList(t[1], uncomment(urls))
    ranked_mirrors = localMirror(rankList(t[1]))
    writeList(mfile, ranked_mirrors)
    os.remove(t[1])
