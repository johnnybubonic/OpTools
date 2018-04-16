#!/usr/bin/env python3

# Get various information about an SKS keyserver from its status page
# without opening a browser.
# Requires BeautifulSoup4 and (optional but recommended) the lxml module.

# stdlib
import argparse
import datetime
import os
import re
from urllib.request import urlopen, urlparse
# pypi/pip
from bs4 import BeautifulSoup
try:
    import lxml
    bs_parser = 'lxml'
except ImportError:
    bs_parser = 'html.parser'


class KeyStats(object):
    def __init__(self, server, port = None, tls = True, ipv6 = None,
                 proto = 'http', output = 'py', verbose = True):
        self.stats = {'server': {},
                      'keys': 0}
        if verbose:
            self.stats['peers'] = {}
            self.stats['histograms'] = {}
        # Currently I only support scraping the stats page of the keyserver.
        # TODO: Can I do this directly via HKP/HKPS? Is there a python module
        # for it?
        self.port_dflts = {'http': {True: 443,
                                    False: 80,
                                    None: 80}}
        self.server = server
        self.tls = tls
        self.ipv6 = ipv6
        self.verbose = verbose
        self.output = output
        self.proto = proto.lower()
        # TODO: would need to add add'l protocol support here.
        if self.proto in ('http', 'https'):
            self.proto = 'http'
        if not port:
            self.port = self.port_dflts[self.proto][self.tls]
        else:
            self.port = int(port)
        if self.proto == 'http':
            self.getStatsPage()

    def getStatsPage(self):
        if self.proto is not 'http':
            # Something went wrong; this function shouldn't be used for
            # non-http.
            return()
        _str_map = {'Hostname': 'name',
                    'Nodename': 'hostname',
                    'Version': 'version',
                    'Server contact': 'contact',
                    'HTTP port': 'hkp_port',
                    'Recon port': 'recon_port',
                    'Debug level': 'debug'}
        _uri = 'pks/lookup?op=stats'
        _url = '{0}://{1}:{2}/{3}'.format(('https' if self.tls else 'http'),
                                          self.server,
                                          self.port,
                                          _uri)
        with urlopen(_url) as u:
            _webdata = u.read()
        _soup = BeautifulSoup(_webdata, bs_parser)
        for e in _soup.find_all('h2'):
            # General server info
            if e.text == 'Settings':
                t = e.find_next('table',
                                attrs = {'summary': 'Keyserver Settings'})
                for r in t.find_all('tr'):
                    h = None
                    row = [re.sub(':$', '',
                                  i.text.strip()) for i in r.find_all('td')]
                    h = row[0]
                    if h in _str_map.keys():
                        if _str_map[h] in ('debug', 'hkp_port', 'recon_port'):
                            self.stats['server'][_str_map[h]] = int(row[1])
                        elif _str_map[h] == 'version':
                            self.stats['server'][_str_map[h]] = tuple(
                                                            row[1].split('.'))
                        else:
                            self.stats['server'][_str_map[h]] = row[1]
            # "Gossip" (recon) peers list
            elif e.text == 'Gossip Peers' and self.verbose:
                self.stats['peers']['recon'] = []
                t = e.find_next('table',
                                attrs = {'summary': 'Gossip Peers'})
                for r in t.find_all('tr'):
                    _peer = list(r.children)[0].text.split()
                    # A tuple consisting of host/name, port.
                    self.stats['peers']['recon'].append((_peer[0],
                                                         int(_peer[1])))
            # Mailsync peers list
            elif e.text == 'Outgoing Mailsync Peers' and self.verbose:
                self.stats['peers']['mailsync'] = []
                t = e.find_next('table', attrs = {'summary': 'Mailsync Peers'})
                for r in t.find_all('tr'):
                    _address = list(r.children)[0].text.strip()
                    self.stats['peers']['mailsync'].append(_address)
            # Number of keys
            elif e.text == 'Statistics':
                self.stats['keys'] = int(e.find_next('p').text.split()[-1])
        # Histograms
        for e in _soup.find_all('h3'):
            # Dailies
            if e.text == 'Daily Histogram' and self.verbose:
                _dfmt = '%Y-%m-%d'
                t = e.find_next('table', attrs = {'summary': 'Statistics'})
                for r in t.find_all('tr'):
                    row = [i.text.strip() for i in r.find_all('td')]
                    if row[0] == 'Time':
                        continue
                    _date = datetime.datetime.strptime(row[0], _dfmt)
                    _new = int(row[1])
                    _updated = int(row[2])
                    # JSON can't convert datetime objects to strings
                    # automatically like PyYAML can.
                    if self.output == 'json':
                        k = str(_date)
                    else:
                        k = _date
                    self.stats['histograms'][k] = {'total': {'new': _new,
                                                             'updated': \
                                                                    _updated},
                                                   'hourly': {}}
            # Hourlies
            elif e.text == 'Hourly Histogram' and self.verbose:
                _dfmt = '%Y-%m-%d %H'
                t = e.find_next('table', attrs = {'summary': 'Statistics'})
                for r in t.find_all('tr'):
                    row = [i.text.strip() for i in r.find_all('td')]
                    if row[0] == 'Time':
                        continue
                    _date = datetime.datetime.strptime(row[0], _dfmt)
                    _new = int(row[1])
                    _updated = int(row[2])
                    _day = datetime.datetime(year = _date.year,
                                             month = _date.month,
                                             day = _date.day)
                    if self.output == 'json':
                        k1 = str(_day)
                        k2 = str(_date)
                    else:
                        k1 = _day
                        k2 = _date
                    self.stats['histograms'][k1]['hourly'][k2] = {'new': _new,
                                                                  'updated': \
                                                                     _updated}
        return()

    def print(self):
        if self.output == 'json':
            import json
            print(json.dumps(self.stats,
                             #indent = 4,
                             default = str))
        elif self.output == 'yaml':
            has_yaml = False
            if 'YAML_MOD' in os.environ.keys():
                _mod = os.environ['YAML_MOD']
                try:
                    import importlib
                    yaml = importlib.import_module(_mod)
                    has_yaml = True
                except (ImportError, ModuleNotFoundError):
                    raise RuntimeError(('Module "{0}" is not ' +
                                        'installed').format(_mod))
            else:
                try:
                    import yaml
                    has_yaml = True
                except ImportError:
                    pass
                try:
                    import pyaml as yaml
                    has_yaml = True
                except ImportError:
                    pass
            if not has_yaml:
                raise RuntimeError(('You must have the PyYAML or pyaml ' +
                                    'module installed to use YAML ' +
                                    'formatting'))
            print(yaml.dump(self.stats))
        elif self.output == 'py':
            import pprint
            pprint.pprint(self.stats)
        return()

def parseArgs():
    args = argparse.ArgumentParser()
    args.add_argument('-i', '--insecure',
                      dest = 'tls',
                      action = 'store_false',
                      help = ('If specified, do not use TLS encryption ' +
                              'querying the server (default is to use TLS)'))
    args.add_argument('-P', '--port',
                      dest = 'port',
                      type = int,
                      default = None,
                      help = ('The port number to use. If not specified, ' +
                              'use the default port per the normal protocol ' +
                              '(i.e. for HTTPS, use 443)'))
    fmt = args.add_mutually_exclusive_group()
    fmt.add_argument('-j', '--json',
                     default = 'py',
                     dest = 'output',
                     action = 'store_const',
                     const = 'json',
                     help = ('Output the data in JSON format'))
    fmt.add_argument('-y', '--yaml',
                     default = 'py',
                     dest = 'output',
                     action = 'store_const',
                     const = 'yaml',
                     help = ('Output the data in YAML format (requires ' +
                             'PyYAML or pyaml module). You can prefer which ' +
                             'one by setting an environment variable, ' +
                             'YAML_MOD, to "yaml" or "pyaml" (for PyYAML or ' +
                             'pyaml respectively); otherwise preference ' +
                             'will be PyYAML > pyaml'))
    fmt.add_argument('-p', '--python',
                     default = 'py',
                     dest = 'output',
                     action = 'store_const',
                     const = 'py',
                     help = ('Output the data in pythonic format (default)'))
    args.add_argument('-v', '--verbose',
                      dest = 'verbose',
                      action = 'store_true',
                      help = ('If specified, print out ALL info (peers, ' +
                              'histogram, etc.), not just the settings/' +
                              'number of keys/contact info/server info'))
    proto_grp = args.add_mutually_exclusive_group()
    proto_grp.add_argument('-4', '--ipv4',
                           dest = 'ipv6',
                           default = None,
                           action = 'store_false',
                           help = ('If specified, force IPv4 (default is ' +
                                   'system\'s preference)'))
    proto_grp.add_argument('-6', '--ipv6',
                           dest = 'ipv6',
                           default = None,
                           action = 'store_true',
                           help = ('If specified, force IPv6 (default is ' +
                                   'system\'s preference)'))
    args.add_argument('server',
                      help = ('The keyserver ((sub)domain, IP address, etc.)'))
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    import pprint
    #pprint.pprint(args)
    ks = KeyStats(**args)
    ks.print()

if __name__ == '__main__':
    main()
