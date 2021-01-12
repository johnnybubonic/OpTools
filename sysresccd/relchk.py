#!/usr/bin/env python3

# TODO: logging

import datetime
import json
import hashlib
import pathlib
import os
import re
import shutil
# import subprocess
##
import psutil
import requests
from lxml import etree


class Updater(object):
    _fname_re = re.compile(r'^systemrescue-(?P<version>[0-9.]+)-(?P<arch>(i686|amd64)).iso$')
    _def_hash = 'sha256'
    _allowed_hashes = ('sha256', 'sha512')
    _allowed_arches = ('i686', 'amd64')
    _date_fmt = '%a, %d %b %Y %H:%M:%S %z'

    def __init__(self,
                 arch = 'amd64',
                 dest_dir = '/boot/iso',
                 dest_file = 'sysresccd.iso',
                 ver_file = '.sysresccd.json',
                 lock_path = '/tmp/.sysresccd.lck',
                 feed_url = 'https://osdn.net/projects/systemrescuecd/storage/!rss',
                 dl_base = 'https://osdn.net/frs/redir.php?m=constant&f=/storage/g/s/sy/systemrescuecd',
                 grub_cfg = '/etc/grub.d/40_custom_sysresccd',
                 # check_gpg = True,  # TODO: GPG sig checking
                 hash_type = 'sha512'):
        if arch.lower() not in self._allowed_arches:
            raise ValueError('arch must be one of: {0}'.format(', '.join(self._allowed_arches)))
        else:
            self.arch = arch.lower()
        if hash_type.lower() not in self._allowed_hashes:
            raise ValueError('hash_type must be one of: {0}'.format(', '.join(self._allowed_hashes)))
        else:
            self.hash_type = hash_type.lower()
        self.dest_dir = os.path.abspath(os.path.expanduser(dest_dir))
        self.dest_file = dest_file
        self.ver_file = ver_file
        self.feed_url = feed_url
        self.dl_base = dl_base
        self.grub_cfg = grub_cfg
        self.lckfile = os.path.abspath(os.path.expanduser(lock_path))
        self.hasher = hashlib.new(self.hash_type)
        self.old_date = None
        self.old_ver = None
        self.old_hash = None
        self.new_date = None
        self.new_ver = None
        self.new_hash = None
        self.do_update = False
        self.force_update = False
        self.iso_url = None
        self.dest_iso = os.path.join(self.dest_dir, self.dest_file)
        self.dest_ver = os.path.join(self.dest_dir, self.ver_file)
        self._init_vars()

    def _init_vars(self):
        if self.getRunning():
            return(None)
        self.getCurVer()
        self.getNewVer()
        return(None)

    def main(self):
        if self.getRunning():
            return(None)
        self.lock()
        if self.do_update or \
                self.force_update or not \
                all((self.old_date,
                     self.old_ver,
                     self.old_hash)):
            self.download()
        self.touchVer()
        self.unlock()
        return(None)

    def download(self):
        if self.getRunning():
            return(None)
        if not any((self.do_update, self.force_update)):
            return(None)
        if not self.iso_url:
            raise RuntimeError('iso_url attribute must be set first')
        req = requests.get(self.iso_url, stream = True)
        if not req.ok:
            raise RuntimeError('Received non-200/30x for {0}'.format(self.iso_url))
        with req as uri:
            with open(self.dest_iso, 'wb') as fh:
                shutil.copyfileobj(uri.raw, fh)
        with open(self.dest_iso, 'rb') as fh:
            self.hasher.update(fh.read())
        self.new_hash = self.hasher.hexdigest().lower()
        self.hasher = hashlib.new(self.hash_type)
        self.updateVer()
        return(None)

    def getCurVer(self):
        if self.getRunning():
            return(None)
        if not os.path.isfile(self.dest_ver):
            self.do_update = True
            self.force_update = True
            self.old_ver = 0.00
            return(None)
        with open(self.dest_ver, 'rb') as fh:
            ver_info = json.load(fh)
        tz_data = datetime.timezone(datetime.timedelta(hours = 0), 'UTC')
        self.old_date = datetime.datetime.fromtimestamp(ver_info['date']).replace(tzinfo = tz_data)
        self.old_ver = ver_info['ver']
        self.old_hash = ver_info.get(self.hash_type, self._def_hash)
        if ver_info.get('arch') != self.arch:
            self.do_update = True
            self.force_update = True
        try:
            with open(self.dest_iso, 'rb') as fh:
                self.hasher.update(fh.read())
            if self.old_hash != self.hasher.hexdigest().lower():
                self.do_update = True
                self.force_update = True
            self.hasher = hashlib.new(self.hash_type)
        except FileNotFoundError:
            return(None)
        return (None)

    def getNewVer(self):
        if self.getRunning():
            return(None)
        req = requests.get(self.feed_url)
        if not req.ok:
            raise RuntimeError('Received non-200/30x for {0}'.format(self.feed_url))
        feed = etree.fromstring(req.content)
        for item in feed.xpath('//item'):
            date_xml = item.find('pubDate')
            title_xml = item.find('title')
            link_xml = item.find('link')
            date = title = link = None
            if date_xml is not None:
                date = datetime.datetime.strptime(date_xml.text, self._date_fmt)
            if title_xml is not None:
                title = title_xml.text
            if link_xml is not None:
                link = link_xml.text
            fname_r = self._fname_re.search(os.path.basename(title))
            if not fname_r:
                continue
            ver_info = fname_r.groupdict()
            if ver_info['arch'] != self.arch:
                continue
            new_ver = float(ver_info.get('version', self.old_ver))
            if not all((self.old_ver, self.old_date)) or \
                    (new_ver > self.old_ver) or \
                    (self.old_date < date):
                self.do_update = True
                self.new_ver = new_ver
                self.new_date = date
                self.iso_url = link
                hash_url = '{0}.{1}'.format(self.iso_url, self.hash_type)
                req = requests.get(hash_url)
                if not req.ok:
                    raise RuntimeError('Received non-200/30x for {0}'.format(hash_url))
                self.new_hash = req.content.decode('utf-8').lower()
        return(None)

    def getRunning(self):
        if not os.path.isfile(self.lckfile):
            return(False)
        my_pid = os.getpid()
        with open(self.lckfile, 'r') as fh:
            pid = int(fh.read().strip())
        if not psutil.pid_exists(pid):
            os.remove(self.lckfile)
            return(False)
        if pid == my_pid:
            return(False)
        return(True)

    def lock(self):
        with open(self.lckfile, 'w') as fh:
            fh.write(str(os.getpid()))
        return(None)

    def touchVer(self):
        if self.getRunning():
            return(None)
        ver_path = pathlib.Path(self.dest_ver)
        ver_path.touch(exist_ok = True)
        return(None)

    def unlock(self):
        if os.path.isfile(self.lckfile):
            os.remove(self.lckfile)
        return(None)

    def updateVer(self):
        if self.getRunning():
            return(None)
        d = {'date': self.new_date.timestamp(),
             'arch': self.arch,
             'ver': self.new_ver,
             self.hash_type: self.new_hash}
        with open(os.path.join(self.dest_dir, self.ver_file), 'w') as fh:
            fh.write(json.dumps(d, indent = 4))
            fh.write('\n')
        return(None)


if __name__ == '__main__':
    u = Updater()
    u.main()
