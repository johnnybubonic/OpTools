#!/usr/bin/env python3

# NOTE: This was written for systemd systems only.
# Tweaking would be needed for non-systemd systems
# (since every non-systemd uses their own init system callables...)

# https://www.jcea.es/programacion/pybsddb_doc/
#import bsddb3  # python-bsddb in arch repos; needed for future features (DB recovery etc.)? possible to dump directly and skip sks dump?
import datetime
import os
import subprocess

NOW = datetime.datetime.utcnow()
NOWstr = NOW.strftime('%Y-%m-%d')

sks = {
       # chowning
       'user': 'sks',
       # chowning
       'group': 'sks',
       # Where your SKS DB is
       'basedir': '/var/lib/sks',
       # Where the dumps should go
       'destdir': '/srv/http/sks/dumps',
       # If None, don't compress dumps. If one of: 'xz', 'gz', 'bz2', then use that compression algo.
       'compress': 'xz',
       # The service name(s) to stop for the dump and to start again afterwards.
       'svcs': ['sks-db', 'sks-recon'],
       # We take sort of take approach #3 here. Sort of.
       # https://bitbucket.org/skskeyserver/sks-keyserver/wiki/DumpingKeys
       'wrkspc': '/var/tmp/sks',
       # I would hope this is self-explanatory.
       'logfile': '/var/log/sksdump.log',
       # If not None value, where we should push the dumps when done. Can be a local path too, obviously.
       'rsync': 'root@sks.mirror.square-r00t.net:/srv/http/sks/dumps/.',
       # How many previous days of dumps should we keep?
       'days': 1
}


def svcMgmt(op):
       if op not in ('start', 'stop'):
              raise ValueError('Operation must be start or stop')
       for svc in sks['svcs']:
              subprocess.run(['systemctl', op, svc])
       return()

def destPrep():
       destdir = os.path.abspath(os.path.expanduser(sks['destdir']))
       PAST = NOW - datetime.timedelta(days = sks['days'])
       pastdir = os.path.join(destdir, YESTERDAY.strftime('%Y-%m-%d'))


def dumpDB():
       pass

def main():
       svcMgmt('stop')
       dumpDB()
       svcMgmt('start')

if __name__ == '__main__':
       pass
       #main()

import pprint
pprint.pprint(sks)
