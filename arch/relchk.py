#!/usr/bin/env python3

# TODO: logging
# Example .arch.json:
# {
#     "date": "Fri, 01 Jan 2021 00:00:00 +0000",
#     "mirror": "http://arch.mirror.constant.com/",
#     "country": "US",
#     "notes": "https://archlinux.org/releng/releases/2021.01.01/",
#     "ver": "2021.01.01",
#     "sha1": "c3082b13d3cf0a253e1322568f2fd07479f86d52"
# }

import datetime
import json
import hashlib
import os
import pathlib
import re
import shutil
##
import psutil
import requests
from lxml import etree
##
import arch_mirror_ranking  # <optools>/arch/arch_mirror_ranking.py


class Updater(object):
    _fname_re = re.compile(r'^archlinux-(?P<version>[0-9]{4}\.[0-9]{2}\.[0-9]{2})-(?P<arch>(i686|x86_64)).iso$')
    _def_hash = 'sha1'
    _allowed_hashes = ('md5', 'sha1')
    _allowed_arches = ('x86_64', )
    _date_fmt = '%a, %d %b %Y %H:%M:%S %z'
    _datever_fmt = '%Y.%m.%d'
    _arch = 'x86_64'  # Arch Linux proper only offers x86_64.
    _iso_dir = 'iso/latest'
    _iso_file = os.path.join(_iso_dir, 'archlinux-{ver}-{arch}.iso')

    def __init__(self,
                 dest_dir = '/boot/iso',
                 dest_file = 'arch.iso',
                 ver_file = '.arch.json',
                 lock_path = '/tmp/.arch.lck',
                 feed_url = 'https://archlinux.org/feeds/releases/',
                 grub_cfg = '/etc/grub.d/40_custom_arch',
                 # check_gpg = True,  # TODO: GPG sig checking
                 hash_type = 'sha1'):
        # if arch.lower() not in self._allowed_arches:
        #     raise ValueError('arch must be one of: {0}'.format(', '.join(self._allowed_arches)))
        # else:
        #     self._arch = arch.lower()
        if hash_type.lower() not in self._allowed_hashes:
            raise ValueError('hash_type must be one of: {0}'.format(', '.join(self._allowed_hashes)))
        else:
            self.hash_type = hash_type.lower()
        self.dest_dir = os.path.abspath(os.path.expanduser(dest_dir))
        self.dest_file = dest_file
        self.ver_file = ver_file
        self.feed_url = feed_url
        self.grub_cfg = grub_cfg
        self.lckfile = os.path.abspath(os.path.expanduser(lock_path))
        # From the JSON.
        self.rel_notes_url = None
        self.old_date = None
        self.old_ver = None
        self.old_hash = None
        self.mirror_base = None
        self.country = None
        # New vals.
        self.new_date = None
        self.new_ver = None
        self.new_hash = None
        # Instance vars again.
        self.do_update = False
        self.force_update = False
        self.iso_url = None
        self.ipv4 = True
        self.ipv6 = False
        self.dest_iso = os.path.join(self.dest_dir, self.dest_file)
        self.dest_ver = os.path.join(self.dest_dir, self.ver_file)
        self._init_vars()

    def _init_vars(self):
        if self.getRunning():
            return(None)
        self.getCountry()
        self.getNet()
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
            self.do_update = True
            self.findMirror()
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
        req = requests.get(self.iso_url, stream = True, headers = {'User-Agent': 'curl/7.74.0'})
        if not req.ok:
            raise RuntimeError('Received non-200/30x {0} for {1}'.format(req.status_code, self.iso_url))
        with req as uri:
            with open(self.dest_iso, 'wb') as fh:
                shutil.copyfileobj(uri.raw, fh)
        hasher = hashlib.new(self.hash_type)
        with open(self.dest_iso, 'rb') as fh:
            hasher.update(fh.read())
        realhash = hasher.hexdigest().lower()
        if realhash != self.new_hash:
            raise RuntimeError('Hash mismatch: {0} (LOCAL), {1} (REMOTE)'.format(realhash, self.new_hash))
        self.updateVer()
        return(None)

    def findMirror(self):
        self.getCountry()
        if self.mirror_base:
            return(None)
        for p in ('http', 'https'):
            m = arch_mirror_ranking.MirrorIdx(country = self.country,
                                              proto = 'http',
                                              is_active = True,
                                              ipv4 = self.ipv4,
                                              ipv6 = self.ipv6,
                                              isos = True,
                                              statuses = False)
            for s in m.ranked_servers:
                try:
                    req = requests.get(s['url'])
                    if req.ok:
                        self.mirror_base = s['url']
                        break
                except (OSError, ConnectionRefusedError):
                    continue
        return(None)

    def getCountry(self):
        if self.country:  # The API has limited number of accesses for free.
            return(None)
        url = 'https://ipinfo.io/country'
        req = requests.get(url, headers = {'User-Agent': 'curl/7.74.0'})
        if not req.ok:
            raise RuntimeError('Received non-200/30x {0} for {1}'.format(req.status_code, url))
        self.country = req.content.decode('utf-8').strip().upper()
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
        self.old_date = datetime.datetime.strptime(ver_info['date'], self._date_fmt)
        self.old_ver = datetime.datetime.strptime(ver_info['ver'], self._datever_fmt)
        self.old_hash = ver_info.get(self.hash_type, self._def_hash)
        self.country = ver_info.get('country')
        self.new_hash = self.old_hash
        self.new_ver = self.old_ver
        self.new_date = self.old_date
        # if ver_info.get('arch') != self._arch:
        #     self.do_update = True
        #     self.force_update = True
        try:
            hasher = hashlib.new(self.hash_type)
            with open(self.dest_iso, 'rb') as fh:
                hasher.update(fh.read())
            if self.old_hash != hasher.hexdigest().lower():
                self.do_update = True
                self.force_update = True
        except FileNotFoundError:
            self.do_update = True
            self.force_update = True
            return(None)
        return(None)

    def getNet(self):
        for k in ('ipv4', 'ipv6'):
            url = 'https://{0}.clientinfo.square-r00t.net'.format(k)
            try:
                req = requests.get(url)
                setattr(self, k, req.json()['ip'])
            except OSError:
                setattr(self, k, False)
        return(None)

    def getNewVer(self):
        if self.getRunning():
            return(None)
        if not self.mirror_base:
            self.findMirror()
        req = requests.get(self.feed_url, headers = {'User-Agent': 'curl/7.74.0'})
        if not req.ok:
            raise RuntimeError('Received non-200/30x {0} for {1}'.format(req.status_code, self.feed_url))
        feed = etree.fromstring(req.content)
        for item in feed.xpath('//item'):
            date_xml = item.find('pubDate')
            ver_xml = item.find('title')
            notes_xml = item.find('link')
            date = ver = notes = None
            if date_xml is not None:
                date = datetime.datetime.strptime(date_xml.text, self._date_fmt)
            if ver_xml is not None:
                ver = ver_xml.text
            if notes_xml is not None:
                notes = notes_xml.text
            new_ver = datetime.datetime.strptime(ver, self._datever_fmt)
            if not all((self.old_ver, self.old_date)) or \
                    (new_ver > self.old_ver) or \
                    (self.old_date < date):
                self.do_update = True
                self.new_ver = new_ver
                self.new_date = date
                self.rel_notes_url = notes
                datever = self.new_ver.strftime(self._datever_fmt)
                self.iso_url = os.path.join(self.mirror_base,
                                            self._iso_file.lstrip('/')).format(ver = datever, arch = self._arch)
                hash_url = os.path.join(self.mirror_base,
                                        self._iso_dir,
                                        '{0}sums.txt'.format(self.hash_type))
                req = requests.get(hash_url, headers = {'User-Agent': 'curl/7.74.0'})
                if not req.ok:
                    raise RuntimeError('Received non-200/30x {0} for {1}'.format(req.status_code, hash_url))
                hash_lines = req.content.decode('utf-8').strip().splitlines()
                tgt_fname = os.path.basename(self.iso_url)
                for line in hash_lines:
                    if line.strip().startswith('#'):
                        continue
                    hash_str, fname = line.split()
                    if fname != tgt_fname:
                        continue
                    self.new_hash = hash_str.lower()
                    break
            break
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
        d = {'date': self.new_date.strftime(self._date_fmt),
             'mirror': self.mirror_base,
             'country': self.country,
             'notes': self.rel_notes_url,
             'ver': self.new_ver.strftime(self._datever_fmt),
             self.hash_type: self.new_hash}
        j = json.dumps(d, indent = 4)
        with open(self.dest_ver, 'w') as fh:
            fh.write(j)
            fh.write('\n')
        return(None)


if __name__ == '__main__':
    u = Updater()
    u.main()
