#!/usr/bin/env python

import argparse
import json
import os
import sqlite3
import run
from urllib.request import urlopen

def parseArgs():
    args = argparse.ArgumentParser(description = ('Modify (add/remove) packages for use with Autopkg'),
                                   epilog = ('Operation-specific help; try e.g. "add --help"'))
    commonargs = argparse.ArgumentParser(add_help = False)
    commonargs.add_argument('-n', '--name',
                            dest = 'pkgnm',
                            required = True,
                            help = ('The name of the PACKAGE to operate on.'))
    commonargs.add_argument('-d', '--db',
                            dest = 'dbfile',
                            default = '~/.optools/autopkg.sqlite3',
                            help = ('The location of the package database. THIS SHOULD NOT BE ANY FILE USED BY '
                                    'ANYTHING ELSE! A default one will be created if it doesn\'t exist'))
    subparsers = args.add_subparsers(help = ('Operation to perform'),
                                     metavar = 'OPERATION',
                                     dest = 'oper')
    addargs = subparsers.add_parser('add',
                                    parents = [commonargs],
                                    help = ('Add a package. If a matching package NAME exists (-n/--name), '
                                            'we\'ll replace it'))
    addargs.add_argument('-b', '--base',
                         dest = 'pkgbase',
                         default = None,
                         help = ('The pkgbase; only really needed for split-packages and we will automatically '
                                 'fetch if it\'s left blank anyways'))
    addargs.add_argument('-v', '--version',
                         dest = 'pkgver',
                         default = None,
                         help = ('The current version; we will automatically fetch it if it\'s left blank'))
    addargs.add_argument('-l', '--lock',
                         dest = 'active',
                         action = 'store_false',
                         help = ('If specified, the package will still exist in the DB but it will be marked inactive'))
    rmargs = subparsers.add_parser('rm',
                                   parents = [commonargs],
                                   help = ('Remove a package from the DB'))
    buildargs = subparsers.add_parser('build',
                                      help = ('Build all packages; same effect as running run.py'))
    buildargs.add_argument('-d', '--db',
                           dest = 'dbfile',
                           default = '~/.optools/autopkg.sqlite3',
                           help = ('The location of the package database. THIS SHOULD NOT BE ANY FILE USED BY '
                                   'ANYTHING ELSE! A default one will be created if it doesn\'t exist'))
    listargs = subparsers.add_parser('ls',
                                     help = ('List packages (and information about them) only'))
    listargs.add_argument('-d', '--db',
                          dest = 'dbfile',
                          default = '~/.optools/autopkg.sqlite3',
                          help = ('The location of the package database. THIS SHOULD NOT BE ANY FILE USED BY '
                                  'ANYTHING ELSE! A default one will be created if it doesn\'t exist'))
    return(args)

def add(args):
    db = sqlite3.connect(args['dbfile'])
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    if not all((args['pkgbase'], args['pkgver'])):
        # We need some additional info from the AUR API...
        aur_url = 'https://aur.archlinux.org/rpc/?v=5&type=info&by=name&arg%5B%5D={0}'.format(args['pkgnm'])
        with urlopen(aur_url) as url:
            aur = json.loads(url.read().decode('utf-8'))['results']
        if not aur:
            raise ValueError(('Either something is screwy with our network access '
                              'or the package {0} doesn\'t exist').format(args['pkgnm']))
        if ((aur['PackageBase'] != aur['Name']) and (not args['pkgbase'])):
            args['pkgbase'] = aur['PackageBase']
        if not args['pkgver']:
            args['pkgver'] = aur['Version']
    cur.execute("SELECT id, pkgname, pkgbase, pkgver, active FROM packages WHERE pkgname = ?",
                (args['pkgnm'], ))
    row = cur.fetchone()
    if row:
        if args['pkgbase']:
            q = ("UPDATE packages SET pkgbase = ? AND pkgver = ? AND ACTIVE = ? WHERE id = ?",
                 (args['pkgbase'], args['pkgver'], ('0' if args['lock'] else '1'), row['id']))
        else:
            q = ("UPDATE packages SET pkgver = ? AND ACTIVE = ? WHERE id = ?",
                 (args['pkgver'], ('0' if args['lock'] else '1'), row['id']))
    else:
        if args['pkgbase']:
            q = (("INSERT INTO "
                    "packages (pkgname, pkgbase, pkgver, active) "
                    "VALUES (?, ?, ?, ?)"),
                 (args['pkgnm'], args['pkgbase'], args['pkgver'], ('0' if args['lock'] else '1')))
        else:
            q = (("INSERT INTO "
                    "packages (pkgname, pkgver, active) "
                    "VALUES (?, ?, ?)"),
                 (args['pkgnm'], args['pkgver'], ('0' if args['lock'] else '1')))
    cur.execute(*q)
    db.commit()
    cur.close()
    db.close()
    return()

def rm(args):
    db = sqlite3.connect(args['dbfile'])
    cur = db.cursor()
    cur.execute("DELETE FROM packages WHERE pkgname = ?",
                (args['pkgnm'], ))
    db.commit()
    cur.close()
    db.close()
    return()

def build(args):
    pm = run.PkgMake(db = args['dbfile'])
    pm.main()
    return()

def ls(args):
    db = sqlite3.connect(args['dbfile'])
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    rows = []
    cur.execute("SELECT * FROM packages ORDER BY pkgname")
    for r in cur.fetchall():
        pkgnm = r['pkgname']
        rows.append({'name': r['pkgname'],
                     'row_id': r['id'],
                     'pkgbase': ('' if not r['pkgbase'] else r['pkgbase']),
                     'ver': r['pkgver'],
                     'enabled': ('Yes' if r['active'] else 'No')})
    header = '|      NAME      |  PACKAGE BASE  | VERSION | ENABLED | ROW ID |'
    sep = '=' * len(header)
    fmt = '|{name:<16}|{pkgbase:<16}|{ver:^9}|{enabled:^9}|{row_id:<8}|'
    out = []
    for row in rows:
        out.append(fmt.format(**row))
    header = '\n'.join((sep, header, sep))
    out.insert(0, header)
    out.append(sep)
    print('\n'.join(out))
    cur.close()
    db.close()
    return()

def main():
    rawargs = parseArgs()
    args = vars(rawargs.parse_args())
    if not args['oper']:
        rawargs.print_help()
        exit()
    args['dbfile'] = os.path.abspath(os.path.expanduser(args['dbfile']))
    if args['oper'] == 'add':
        add(args)
    elif args['oper'] == 'rm':
        rm(args)
    elif args['oper'] == 'build':
        build(args)
    elif args['oper'] == 'ls':
        ls(args)
    return()

if __name__ == '__main__':
    main()
