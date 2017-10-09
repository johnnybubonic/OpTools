#!/usr/bin/env python3

import argparse
import csv
import datetime
import difflib
import hashlib
import lzma
import os
import pickle
from urllib.request import urlopen

# TODO: to avoid race conditions, we should probably simply ignore/remove
# timestamps and just touch the cache file whenever checking.

class website(object):
    def __init__(self, args, csvline):
        # Field names
        self.fnames = ('UUID', 'url', 'checksum', 'timestamp')
        self.args = args
        self.parseCSV([csvline])
        self.cache = args['cache_dir']
        self.cacheControl()
        self.remoteFetch()
        return

    def parseCSV(self, data):
        _rows = csv.DictReader(data,
                               fieldnames = self.fnames,
                               delimiter = ',',
                               quotechar = '"')
        for r in _rows:
            self.meta = r
            break  # We only want one, so if we SOMEHOW got more than one line...
        return()

    def cacheControl(self):
        os.makedirs(self.cache, exist_ok = True)
        self.site = {}
        _cachefile = os.path.join(self.cache, self.meta['UUID'])
        if os.path.isfile(_cachefile):
            with lzma.open(_cachefile, mode = 'rb') as f:
                self.site['local'] = pickle.load(f)
        else:
            with urlopen(self.meta['url']) as _site,\
                 lzma.open(_cachefile,
                           mode = 'wb',
                           check = lzma.CHECK_SHA256,
                           preset = 9|lzma.PRESET_EXTREME) as f:
                _data = _site.read().decode('utf-8')
                pickle.dump(_data, f)
                self.site['local'] = _data
                self.meta['timestamp'] = str(int(datetime.datetime.now().timestamp()))
                _hash = hashlib.sha256(self.site['local'].encode('utf-8'))
                self.meta['checksum'] = str(_hash.hexdigest())
        return()

    def remoteFetch(self):
        with urlopen(self.meta['url']) as _site:
            self.site['remote'] = _site.read().decode('utf-8')
        _hash = hashlib.sha256(self.site['remote'].encode('utf-8'))
        self.site['remotesum'] = str(_hash.hexdigest())
        self.meta['timestamp'] = str(int(datetime.datetime.now().timestamp()))
        return()

    def compare(self):
        # Don't even compare if the checksums match.
        if self.site['remotesum'] == self.meta['checksum']:
            self.diff = None
            #print('{0}: Doing nothing'.format(self.meta['UUID']))
            return()
        print('{{{0}}}: "{1}":'.format(self.meta['UUID'], self.meta['url']))
        diff = difflib.unified_diff(self.site['local'].splitlines(1),
                                    self.site['remote'].splitlines(1))
        self.diff = ''.join(diff)
        print(self.diff)
        with urlopen(self.meta['url']) as _site,\
                 lzma.open(os.path.join(self.cache, self.meta['UUID']),
                           mode = 'wb',
                           check = lzma.CHECK_SHA256,
                           preset = 9|lzma.PRESET_EXTREME) as f:
                _data = _site.read().decode('utf-8')
                pickle.dump(_data, f)
        return()

    def writeCSV(self):
        #if self.diff:  # We actually WANT to write, because we're updating the last fetch timestamp.
        _lines = []
        with open(self.args['urls_csv'], 'r') as f:
            _f = f.read()
        _rows = csv.DictReader(_f.splitlines(),
                               fieldnames = self.fnames,
                               delimiter = ',',
                               quotechar = '"')
        for r in _rows:
            _uuid = r['UUID']
            if _uuid == self.meta['UUID']:
                r['checksum'] = self.site['remotesum']
                r['timestamp'] = self.meta['timestamp']
            _lines.append(r)
        with open(self.args['urls_csv'], 'w', newline = '') as f:
            _w = csv.DictWriter(f,
                                fieldnames = self.fnames,
                                delimiter = ',',
                                quotechar = '"',
                                quoting = csv.QUOTE_ALL)
            _w.writerows(_lines)
        return()

def parseArgs():
    # Define defaults
    _self_dir = os.path.dirname(os.path.realpath(__file__))
    _cache_dir = os.path.join(_self_dir, 'cache')
    _urls_csv = os.path.join(_self_dir, 'urls.csv')
    args = argparse.ArgumentParser()
    args.add_argument('-c',
                      '--cache-dir',
                      metavar = '/path/to/cache/dir/',
                      default = _cache_dir,
                      dest = 'cache_dir',
                      type = str,
                      help = ('The path to where cached versions of websites are stored. ' +
                              'They are stored in the python binary "pickle" format. ' +
                              'Default: \n\n\t\033[1m{0}\033[0m').format(_cache_dir))
    args.add_argument('-u',
                      '--urls',
                      metavar = '/path/to/urls.csv',
                      default = _urls_csv,
                      dest = 'urls_csv',
                      type = str,
                      help = ('The path to where a CSV file of the URLs to check should be. ' +
                              'Note that it should be writeable by whatever user the script is running as.' +
                              'See urls.csv.spec for the specification. ' +
                              'Default: \n\n\t\033[1m{0}\033[0m').format(_urls_csv))
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    for d in ('cache_dir', 'urls_csv'):
        args[d] = os.path.realpath(os.path.expanduser(args[d]))
    with open(args['urls_csv'], 'r', newline = '') as f:
        _csv = f.read()
    for line in _csv.splitlines():
        w = website(args, line)
        w.compare()
        w.writeCSV()
        if w.diff:
            print(w.diff)

if __name__ == '__main__':
    main()
