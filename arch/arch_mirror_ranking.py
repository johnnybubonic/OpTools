#!/usr/bin/env python3

import argparse
import datetime
# import dns  # TODO: replace server['ipv4'] with IPv4 address(es)? etc.
import json
import re
import sys
from urllib.request import urlopen
##
import iso3166


servers_json_url = 'https://www.archlinux.org/mirrors/status/json/'
protos = ('http', 'https', 'rsync')


class MirrorIdx(object):
    def __init__(self, country = None, proto = None, is_active = None, json_url = servers_json_url,
                 name_re = None, ipv4 = None, ipv6 = None, isos = None, statuses = False, *args, **kwargs):
        _tmpargs = locals()
        del (_tmpargs['self'])
        for k, v in _tmpargs.items():
            setattr(self, k, v)
        self.validateParams()
        self.servers_json = {}
        self.servers = []
        self.servers_with_scores = []
        self.ranked_servers = []
        self.fetchJSON()
        self.buildServers()
        self.rankServers()

    def fetchJSON(self):
        if self.statuses:
            sys.stderr.write('Fetching servers from {0}...\n'.format(self.json_url))
        with urlopen(self.json_url) as u:
            self.servers_json = json.load(u)
        return()

    def buildServers(self):
        _filters = (self.country, self.proto, self.ipv4, self.ipv6, self.isos, self.name_re)
        if self.statuses:
            sys.stderr.write('Applying filters (if any)...\n')
        for s in self.servers_json['urls']:
            # We handle these as "tri-value" (None, True, False)
            if self.is_active is not None:
                if s['active'] != self.is_active:
                    continue
            if not any(_filters):
                self.servers.append(s.copy())
                if s['score']:
                    self.servers_with_scores.append(s)
                continue
            # These are based on string values.
            if self.name_re:
                if not self.name_re.search(s['url']):
                    continue
            # These are regular True/False switches
            skip = False
            while not skip:
                for value, limiter in (('country_code', self.country), ('protocol', self.proto),
                                       ('ipv4', self.ipv4), ('ipv6', self.ipv6), ('isos', self.isos)):
                    if limiter:
                        if s[value] != limiter:
                            skip = True
            if skip:
                continue
            self.servers.append(s.copy())
        return()

    def rankServers(self):
        if self.statuses:
            sys.stderr.write('Ranking mirrors...\n')
        self.ranked_servers = sorted(self.servers_with_scores, key = lambda i: i['score'])
        return()

    def validateParams(self):
        if self.proto and self.proto.lower() not in protos:
            err = '{0} must be one of: {1}'.format(self.proto, ', '.join([i.upper() for i in protos]))
            raise ValueError(err)
        elif self.proto:
            self.proto = self.proto.upper()
        if self.country and self.country.upper() not in iso3166.countries:
            err = ('{0} must be a valid ISO-3166-1 ALPHA-2 country code. '
                   'See https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes'
                   '#Current_ISO_3166_country_codes').format(self.country)
            raise ValueError()
        elif self.country:
            self.country = self.country.upper()
        if self.name_re:
            self.name_re = re.compile(self.name_re)
        return()


def parseArgs():
    args = argparse.ArgumentParser(description = 'Fetch and rank Arch Linux mirrors',
                                   epilog = ('NOTE: Applying any filters will vastly increase the amount '
                                             'of processing time!'))
    args.add_argument('-c', '--country',
                      dest = 'country',
                      help = ('If specified, limit results to this country (in ISO-3166-1 ALPHA-2 format)'))
    args.add_argument('-p', '--protocol',
                      choices = protos,
                      dest = 'proto',
                      help = ('If specified, limit results to this protocol'))
    args.add_argument('-r', '--name-regex',
                      dest = 'name_re',
                      help = ('If specified, limit results to URLs that match this regex pattern (Python re syntax)'))
    args.add_argument('-4', '--ipv4',
                      dest = 'ipv4',
                      action = 'store_true',
                      help = ('If specified, limit results to servers that support IPv4'))
    args.add_argument('-6', '--ipv6',
                      dest = 'ipv6',
                      action = 'store_true',
                      help = ('If specified, limit results to servers that support IPv6'))
    args.add_argument('-i', '--iso',
                      dest = 'isos',
                      action = 'store_true',
                      help = ('If specified, limit results to servers that have ISO images'))
    is_active = args.add_mutually_exclusive_group()
    is_active.add_argument('-a', '--active-only',
                           default = None,
                           const = True,
                           action = 'store_const',
                           dest = 'is_active',
                           help = ('If specified, only include active servers (default is active + inactive)'))
    is_active.add_argument('-n', '--inactive-only',
                           default = None,
                           const = False,
                           action = 'store_const',
                           dest = 'is_active',
                           help = ('If specified, only include inactive servers (default is active + inactive)'))
    return(args)

if __name__ == '__main__':
    args = vars(parseArgs().parse_args())
    m = MirrorIdx(**args, statuses = True)
    for s in m.ranked_servers:
        print('Server = {0}$repo/os/$arch'.format(s['url']))