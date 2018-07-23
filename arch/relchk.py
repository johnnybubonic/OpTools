#!/usr/bin/env python3

import configparser
import hashlib
import os
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen
try:
    import lxml
    htmlparser = 'lxml'
except ImportError:
    htmlparser = 'html.parser'

cfgpath = os.path.abspath(os.path.expanduser(
                                        '~/.config/optools/relchk/arch.ini'))

cfg = configparser.ConfigParser()
cfg['arch'] = {'url': 'https://arch.mirror.square-r00t.net/iso/latest/',
               'path': '/boot/iso/arch.iso',
               'hashtype': 'sha1',
               'hashurl': (
                'https://arch.mirror.square-r00t.net/iso/latest/sha1sums.txt')
                }

if not os.path.isfile(cfgpath):
    os.makedirs(os.path.dirname(cfgpath), exist_ok = True)
    with open(cfgpath, 'w') as f:
        cfg.write(f)
else:
    cfg.read(cfgpath)

cfg['arch']['path'] = os.path.abspath(os.path.expanduser(cfg['arch']['path']))

# We need the hashes first. We'll pop them into memory,
# no need to save locally.
# Must be in GNU checksum format (i.e. "<HASH>  <FILENAME>\n").
hashes = {}
if 'hashurl' in cfg['arch']:
    with urlopen(cfg['arch']['hashurl']) as h:
        for i in h.read().decode('utf-8').splitlines():
            line = [x.strip() for x in i.split()]
            hashes[os.path.basename(line[1])] = line[0]
chksum = hashlib.new(cfg['arch']['hashtype'])

# Now we (try to) get a list of files available for download. We're looking
# for .iso or .img files. Compressed images not currently supported; TODO.
exts = re.compile('.*\.(iso|img)$', re.IGNORECASE)
imgfiles = []
with urlopen(cfg['arch']['url']) as u:
    dlsoup = BeautifulSoup(u.read().decode('utf-8'), htmlparser)
for a in dlsoup.find_all('a'):
    if a['href']:
        if exts.search(a['href']):
            if not urlparse(a['href']).netloc:
                imgfiles.append(urljoin(cfg['arch']['url'], a['href']))
            else:
                imgfiles.append(a['href'])
if not imgfiles:
    raise RuntimeError('Could not find any ISO or IMG files at {0}'.format(
            cfg['arch']['url']))
# Not foolproof, but will handle standard Arch ISO mirrors just fine.
imgfiles.sort()
iso = imgfiles[0]

# Now we get the existing file (if it exists) and grab the hash (if we have
# one fetched).
up2date = False
if os.path.isfile(cfg['arch']['path']):
    _fname = os.path.basename(iso)
    if _fname in hashes:
        with open(cfg['arch']['path'], 'rb') as f:
            chksum.update(f.read())
        if chksum.hexdigest().lower() == hashes[_fname].lower():
            up2date = True

if not up2date:
    print('Downloading...')
    os.makedirs(os.path.dirname(cfg['arch']['path']), exist_ok = True)
    with open(cfg['arch']['path'], 'wb') as f, urlopen(iso) as u:
        f.write(u.read())
else:
    print('No need to download; we are up to date')

print('Done')
