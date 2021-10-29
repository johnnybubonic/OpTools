#!/usr/bin/env python3

import argparse
import json
import logging
import logging.handlers
import os
import re
import sys
import warnings
##
import dns.exception
import dns.resolver
import requests
##
from lxml import etree
try:
    # https://www.freedesktop.org/software/systemd/python-systemd/journal.html#journalhandler-class
    from systemd import journal
    _has_journald = True
except ImportError:
    _has_journald = False


logfile = '~/.cache/ddns.log'

# Prep the log file.
logfile = os.path.abspath(os.path.expanduser(logfile))
os.makedirs(os.path.dirname(logfile), exist_ok = True, mode = 0o0700)
if not os.path.isfile(logfile):
    with open(logfile, 'w') as fh:
        fh.write('')
os.chmod(logfile, 0o0600)

# And set up logging.
_cfg_args = {'handlers': [],
             'level': logging.DEBUG}
if _has_journald:
    # There were some weird changes somewhere along the line.
    try:
        # But it's *probably* this one.
        h = journal.JournalHandler()
    except AttributeError:
        h = journal.JournaldLogHandler()
    # Systemd includes times, so we don't need to.
    h.setFormatter(logging.Formatter(style = '{',
                                     fmt = ('{name}:{levelname}:{name}:{filename}:'
                                            '{funcName}:{lineno}: {message}')))
    _cfg_args['handlers'].append(h)
h = logging.handlers.RotatingFileHandler(logfile,
                                         encoding = 'utf8',
                                         # Disable rotating for now.
                                         # maxBytes = 50000000000,
                                         # backupCount = 30
                                         )
h.setFormatter(logging.Formatter(style = '{',
                                 fmt = ('{asctime}:'
                                        '{levelname}:{name}:{filename}:'
                                        '{funcName}:{lineno}: {message}')))
_cfg_args['handlers'].append(h)
logging.basicConfig(**_cfg_args)
logger = logging.getLogger('DDNS')
logger.info('Logging initialized.')

is_tty = sys.stdin.isatty()
if not is_tty:
    logger.debug('Not running in an interactive invocation; disabling printing warnings')
else:
    logger.debug('Running in an interactive invocation; enabling printing warnings')


class Updater(object):
    tree = None
    records = {}
    api_base = None
    session = None
    token = None
    my_ips = {4: None, 6: None}
    resolver = dns.resolver.Resolver(configure = False)
    resolver.nameservers = ['64.6.64.6', '64.6.65.6']

    def __init__(self, cfg_path = '~/.config/ddns.xml', *args, **kwargs):
        self.xml = os.path.abspath(os.path.expanduser(cfg_path))
        logger.debug('Updater initialized with config {0}'.format(self.xml))
        self._getConf()
        self._getMyIP()
        self._getSession()

    def _getConf(self):
        try:
            with open(self.xml, 'rb') as fh:
                self.xml = etree.fromstring(fh.read())
        except FileNotFoundError as e:
            logger.error('Configuration file does not exist; please create it')
            raise e
        self.tree = self.xml.getroottree()
        self.token = self.xml.attrib['token']
        self.api_base = re.sub(r'/$', '', self.xml.attrib['base'])
        dom_xml = self.xml.findall('domain')
        num_doms = len(dom_xml)
        logger.debug('Found {0} domains in config'.format(num_doms))
        for idx, d in enumerate(dom_xml):
            domain = d.attrib['name']
            logger.debug('Iterating domain {0} ({1}/{2})'.format(domain, (idx + 1), num_doms))
            if domain not in self.records.keys():
                self.records[domain] = []
            sub_xml = d.findall('sub')
            num_subs = len(sub_xml)
            logger.debug('Found {0} records for domain {1}'.format(num_subs, domain))
            for idx2, s in enumerate(sub_xml):
                logger.debug('Adding record {0}.{1} to index ({2}/{3})'.format(s.text, domain, (idx2 + 1), num_subs))
                self.records[domain].append(s.text)
        return()

    def _getDNS(self, record):
        records = {}
        for t in ('A', 'AAAA'):
            logger.debug('Resolving {0} ({1})'.format(record, t))
            try:
                q = self.resolver.resolve(record, t)
                for a in q:
                    if t not in records.keys():
                        records[t] = []
                    ip = a.to_text()
                    logger.debug('Found IP {0} for record {1} ({2})'.format(ip, record, t))
                    records[t].append(ip)
            except dns.exception.Timeout as e:
                logger.error('Got a timeout when resolving {0} ({1}): {2}'.format(record, t, e))
                continue
            except dns.resolver.NXDOMAIN as e:
                # This is a debug instead of an error because that record type may not exist.
                logger.debug('Record {0} ({1}) does not exist: {2}'.format(record, t, e))
                continue
            except dns.resolver.YXDOMAIN as e:
                logger.error('Record {0} ({1}) is too long: {2}'.format(record, t, e))
                continue
            except dns.resolver.NoAnswer as e:
                # This is a debug instead of an error because that record type may not exist.
                logger.debug('Record {0} ({1}) exists but has no content: {2}'.format(record, t, e))
                continue
            except dns.resolver.NoNameservers as e:
                logger.error(('Could not failover to a non-broken resolver when resolving {0} ({1}): '
                              '{2}').format(record, t, e))
                continue
        return(records)

    def _getMyIP(self):
        for v in self.my_ips.keys():
            try:
                logger.debug('Getting the client\'s WAN address for IPv{0}'.format(v))
                r = requests.get('https://ipv{0}.clientinfo.square-r00t.net/?raw=1'.format(v))
                if not r.ok:
                    logger.error('Got a non-OK response from WAN IPv{0} fetch.'.format(v))
                    raise RuntimeError('Could not get the IPv{0} address'.format(v))
                ip = r.json()['ip']
                logger.debug('Got WAN IP address {0} for IPv{1}'.format(ip, v))
                self.my_ips[v] = ip
            except requests.exceptions.ConnectionError:
                logger.debug('Could not get WAN address for IPv{0}; likely not supported on this network'.format(v))
        return()

    def _getSession(self):
        self.session = requests.Session()
        self.session.headers.update({'Authorization': 'Bearer {0}'.format(self.token)})
        return()

    def update(self):
        for d in self.records.keys():
            d_f = json.dumps({'domain': d})
            doms_url = '{0}/domains'.format(self.api_base)
            logger.debug('Getting list of domains from {0} (filtered to {1})'.format(doms_url, d))
            d_r = self.session.get(doms_url,
                                   headers = {'X-Filter': d_f})
            if not d_r.ok:
                e = 'Could not get list of domains when attempting to check {0}; skipping'.format(d)
                if is_tty:
                    warnings.warn(e)
                logger.warning(e)
                continue
            try:
                d_id = d_r.json()['data'][0]['id']
            except (IndexError, KeyError):
                e = 'Could not find domain {0} in the returned domains list; skipping'.format(d)
                if is_tty:
                    warnings.warn(e)
                logger.warning(e)
                continue
            for s in self.records[d]:
                fqdn = '{0}.{1}'.format(s, d)
                logger.debug('Processing {0}'.format(fqdn))
                records = self._getDNS(fqdn)
                for v, t in ((4, 'A'), (6, 'AAAA')):
                    ip = self.my_ips.get(v)
                    rrset = records.get(t)
                    if not ip:
                        e = 'IPv{0} disabled; skipping'.format(v)
                        if is_tty:
                            warnings.warn(e)
                        logger.warning(e)
                        continue
                    if rrset and ip in rrset:
                        e = 'Skipping adding {0} for {1}; already exists in DNS'.format(ip, fqdn)
                        logger.info(e)
                        if is_tty:
                            print(e)
                        continue
                    s_f = json.dumps({'name': s,
                                      'type': t})
                    records_url = '{0}/domains/{1}/records'.format(self.api_base, d_id)
                    logger.debug(('Getting list of records from {0} '
                                  '(filtered to name {1} and type {2})').format(records_url, s, t))
                    s_r = self.session.get(records_url,
                                           headers = {'X-Filter': s_f})
                    if not s_r.ok:
                        e = 'Could not get list of records when attempting to check {0} ({1}); skipping'.format(fqdn, t)
                        if is_tty:
                            warnings.warn(e)
                        logger.warning(e)
                        continue
                    r_ids = set()
                    # If r_exists is:
                    #   None, then the record exists but the current WAN IP is missing (all records replaced).
                    #   False, then the record does not exist (record will be added).
                    #   True, then the record exists and is current (nothing will be done).
                    r_exists = None
                    try:
                        api_records = s_r.json().pop('data')
                        for idx, r in enumerate(api_records):
                            r_ids.add(r['id'])
                            r_ip = r['target']
                            if r_ip == ip:
                                r_exists = True
                    except (IndexError, KeyError):
                        e = ('Could not find record {0} ({1}) in the returned records list; '
                             'creating new record').format(fqdn, t)
                        if is_tty:
                            print(e)
                        logger.info(e)
                        r_exists = False
                    if r_exists:
                        # Do nothing.
                        e = 'Skipping adding {0} for {1}; already exists in API and is correct'.format(ip, fqdn)
                        logger.info(e)
                        if is_tty:
                            print(e)
                        continue
                    elif r_exists is None:
                        # Remove all records and then add (at the end).
                        # We COULD do an update:
                        #   https://developers.linode.com/api/v4/domains-domain-id-records-record-id/#put
                        # BUT then we break future updating since we don't know which record is the "right" one to
                        # update.
                        logger.debug('Record {0} ({1}) exists but does not contain {2}; replacing'.format(fqdn, t, ip))
                        for r_id in r_ids:
                            del_url = '{0}/{1}'.format(records_url, r_id)
                            logger.debug(('Deleting record ID {0} for {1} ({2})').format(r_id, fqdn, t))
                            del_r = self.session.delete(del_url)
                            if not del_r.ok:
                                e = 'Could not delete record ID {0} for {1} ({2}); skipping'.format(r_id, fqdn, t)
                                if is_tty:
                                    warnings.warn(e)
                                logger.warning(e)
                                continue
                    else:
                        # Create the record.
                        logger.debug('Record {0} ({1}) does not exist; creating'.format(fqdn, ip))
                    record = {'name': s,
                              'type': t,
                              'target': ip,
                              'ttl_sec': 300}
                    create_r = self.session.post(records_url,
                                                 json = record)
                    if not create_r.ok:
                        e = 'Could not create record {0} ({1}); skipping'.format(fqdn, t)
                        if is_tty:
                            warnings.warn(e)
                        logger.warning(e)
                        continue
        return()


def parseArgs():
    args = argparse.ArgumentParser(description = ('Automatically update Linode DNS via their API'))
    args.add_argument('-c', '--config',
                      dest = 'cfg_path',
                      default = '~/.config/ddns.xml',
                      help = ('The path to the configuration file. Default: ~/.config/ddns.xml'))
    return(args)


def main():
    args = parseArgs().parse_args()
    u = Updater(**vars(args))
    u.update()
    return(None)


if __name__ == '__main__':
    main()
