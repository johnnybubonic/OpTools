#!/usr/bin/env python3

# TODO: add config file support

import os
import re
import shutil
import subprocess
##
import requests
from lxml import etree

dest_dir = '/boot/iso'
dest_file = 'sysresccd.iso'
ver_file = '.sysresccd.info'
feed_url = 'https://osdn.net/projects/systemrescuecd/storage/!rss'
dl_base = ('https://osdn.net/frs/'
           'redir.php?m=constant&f='
           '/storage/g/s/sy/systemrescuecd/releases/{version}/systemrescuecd-{version}.iso')
old_version = None
new_version = None
grub_cfg = '/etc/grub.d/40_custom_sysresccd'


def downloadISO(url, version):
    dest = os.path.join(dest_dir, dest_file)
    destver = os.path.join(dest_dir, ver_file)
    with requests.get(url, stream = True) as url:
        with open(dest, 'wb') as fh:
            shutil.copyfileobj(url.raw, fh)
    with open(destver, 'w') as fh:
        fh.write(version.strip())
    return()


if os.path.isfile(os.path.join(dest_dir, ver_file)):
    with open(os.path.join(dest_dir, ver_file), 'r') as f:
        old_version = f.read().strip()
r = requests.get(feed_url)
if not r.ok:
    raise RuntimeError('Could not fetch feed from {0}'.format(feed_url))
feed = etree.fromstring(r.content)
latest = feed.xpath('//item')[0]
raw_version = os.path.basename(latest.find('title').text.strip())
new_version = re.sub(r'^systemrescuecd-(x86-)?(?P<version>[0-9.]+).iso',
                     r'\g<version>',
                     raw_version)
dl_url = dl_base.format(version = new_version)
if old_version and old_version != new_version:
    downloadISO(dl_url, new_version)
elif not old_version:
    downloadISO(dl_url, new_version)
