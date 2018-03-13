#!/usr/bin/env python3

# Thanks to Matt Rude and https://gist.github.com/mattrude/b0ac735d07b0031bb002 so I can know what the hell I'm doing.

import argparse
import configparser
import datetime
import getpass
import os
import subprocess
from pwd import getpwnam
from grp import getgrnam

NOW = datetime.datetime.utcnow()
NOWstr = NOW.strftime('%Y-%m-%d')

# TODO:
# - cleanup/rotation should be optional

cfgfile = os.path.join(os.environ['HOME'], '.config', 'optools', 'sksdump.ini')

def getDefaults():
    # Hardcoded defaults
    dflt = {'system': {'user': 'sks',
                       'group': 'sks',
                       'compress': 'xz',
                       'svcs': ['sks-db', 'sks-recon'],
                       'logfile': '/var/log/sksdump.log',
                       'days': 1,
                       'dumpkeys': 15000},
            'sync': {'throttle': 0},
            'paths': {'basedir': '/var/lib/sks',
                      'destdir': '/srv/http/sks/dumps',
                      'rsync': 'root@mirror.square-r00t.net:/srv/http/sks/dumps'},
            'runtime': {'nodump': None, 'nocompress': None, 'nosync': None}}
    ## Build out the default .ini.
    dflt_str = ('# IMPORTANT: This script uses certain permissions functions that require some forethought.\n' +
                '# You can either run as root, which is the "easy" way, OR you can run as the sks user.\n' +
                '# Has to be one or the other; you\'ll SERIOUSLY mess things up otherwise.\n' +
                '# If you run as the sks user, MAKE SURE the following is set in your sudoers\n' +
                '# (where SKSUSER is the username sks runs as):\n#\tCmnd_Alias SKSCMDS = ' +
                '/usr/bin/systemctl start sks-db,\\\n#\t\t/usr/bin/systemctl stop sks-db,\\\n#\t\t' +
                '/usr/bin/systemctl start sks-recon,\\\n#\t\t/usr/bin/systemctl stop sks-recon\n#\t' +
                'SKSUSER ALL = NOPASSWD: SKSCMDS\n\n')
    dflt_str += ('# This was written for systemd systems only. Tweaking would be needed for non-systemd systems\n' +
                 '# (since every non-systemd uses their own init system callables...)\n\n')
    # [system]
    d = dflt['system']
    dflt_str += ('## SKSDUMP CONFIG FILE ##\n\n# This section controls various system configuration.\n' +
                '[system]\n# This should be the user SKS runs as.\nuser = {0}\n# This is the group that' +
                'SKS runs as.\ngroup = {1}\n# If None, don\'t compress dumps.\n# If one of: ' +
                'xz, gz, bz2, or lrz (for lrzip) then use that compression algo.\ncompress = {2}\n' +
                '# These services will be started/stopped, in order, before/after dumps. ' +
                'Comma-separated.\nsvcs = {3}\n# The path to the logfile.\nlogfile = {4}\n# The number ' +
                'of days of rotated key dumps. If None, don\'t rotate.\ndays = {5}\n# How many keys to include in each ' +
                'dump file.\ndumpkeys = {6}\n\n').format(d['user'],
                                                         d['group'],
                                                         d['compress'],
                                                         ','.join(d['svcs']),
                                                         d['logfile'],
                                                         d['days'],
                                                         d['dumpkeys'])
    # [sync]
    d = dflt['sync']
    dflt_str += ('# This section controls sync settings.\n[sync]\n# This setting is what the speed should be throttled to, '+
                 'in KiB/s. Use 0 for no throttling.\nthrottle = {0}\n\n').format(d['throttle'])
    # [paths]
    d = dflt['paths']
    dflt_str += ('# This section controls where stuff goes and where we should find it.\n[paths]\n# ' +
                 'Where your SKS DB is.\nbasedir = {0}\n# This is the base directory where the dumps should go.\n' +
                 '# There will be a sub-directory created for each date.\ndestdir = {1}\n# The ' +
                 'path for rsyncing the dumps. If None, don\'t rsync.\nrsync = {2}\n\n').format(d['basedir'],
                                                                                                d['destdir'],
                                                                                                d['rsync'])
    # [runtime]
    d = dflt['runtime']
    dflt_str += ('# This section controls runtime options. These can be overridden at the commandline.\n' +
                 '# They take no values; they\'re merely options.\n[runtime]\n# Don\'t dump any keys.\n' +
                 '# Useful for dedicated in-transit/prep boxes.\n;nodump\n# Don\'t compress the dumps, even if ' +
                 'we have a compression scheme specified in [system:compress].\n;nocompress\n# Don\'t sync to' +
                 'another server/path, even if one is specified in [paths:rsync].\n;nosync\n')
    realcfg = configparser.ConfigParser(defaults = dflt, allow_no_value = True)
    if not os.path.isfile(cfgfile):
        with open(cfgfile, 'w') as f:
            f.write(dflt_str)
    realcfg.read(cfgfile)
    return(realcfg)

def svcMgmt(op, args):
    if op not in ('start', 'stop'):
        raise ValueError('Operation must be start or stop')
    for svc in args['svcs'].split(','):
        cmd = ['/usr/bin/systemctl', op, svc.strip()]
        if getpass.getuser() != 'root':
            cmd.insert(0, 'sudo')
        subprocess.run(cmd)
    return()

def destPrep(args):
    nowdir = os.path.join(args['destdir'], NOWstr)
    curdir = os.path.join(args['destdir'], 'current')
    PAST = NOW - datetime.timedelta(days = args['days'])
    for thisdir, dirs, files in os.walk(args['destdir'], topdown = False):
        for f in files:
            try:  # we use a try here because if the link's broken, the script bails out.
                fstat = os.stat(os.path.join(thisdir, f))
                mtime = fstat.st_mtime
                if int(mtime) < PAST.timestamp():
                    os.remove(os.path.join(thisdir, f))
            except FileNotFoundError:  # broken symlink
                try:
                    os.remove(os.path.join(thisdir, f))
                except:
                    pass  # just... ignore it. it's fine, whatever.
            # Delete if empty dir
            if os.path.isdir(thisdir):
                if len(os.listdir(thisdir)) == 0:
                    os.rmdir(thisdir)
        for d in dirs:
            _dir = os.path.join(thisdir, d)
            if os.path.isdir(_dir):
                if len(os.listdir(_dir)) == 0:
                    try:
                        os.rmdir(os.path.join(thisdir, d))
                    except NotADirectoryError:
                        pass  # in case it grabs the "current" symlink
    #try:
    #    os.removedirs(sks['destdir'])  # Remove empty dirs
    #except:
    #    pass  # thisisfine.jpg
    os.makedirs(nowdir, exist_ok = True)
    if getpass.getuser() == 'root':
        uid = getpwnam(args['user']).pw_uid
        gid = getgrnam(args['group']).gr_gid
        for d in (args['destdir'], nowdir):  # we COULD set it as part of the os.makedirs, but iirc it doesn't set it for existing dirs
            os.chown(d, uid, gid)
    if os.path.isdir(curdir):
        os.remove(curdir)
    try:
        os.symlink(NOWstr, curdir, target_is_directory = True)
    except FileExistsError:
        pass  # Ignore if it was set earlier
    return()

def dumpDB(args):
    destPrep(args)
    os.chdir(args['basedir'])
    svcMgmt('stop', args)
    cmd = ['sks',
           'dump',
           str(args['dumpkeys']),  # How many keys per dump?
           os.path.join(args['destdir'], NOWstr),  # Where should it go?
           'keydump.{0}'.format(NOWstr)]  # What the filename prefix should be
    if getpass.getuser() == 'root':
        cmd2 = ['sudo', '-u', args['user']]
        cmd2.extend(cmd)
        cmd = cmd2
    with open(args['logfile'], 'a') as f:
        f.write('===== {0} =====\n'.format(str(datetime.datetime.utcnow())))
        subprocess.run(cmd, stdout = f, stderr = f)
    svcMgmt('start', args)
    return()

def compressDB(args):
    if not args['compress']:
        return()
    curdir = os.path.join(args['destdir'], NOWstr)
    for thisdir, dirs, files in os.walk(curdir):  # I use os.walk here because we might handle this differently in the future...
        files.sort()
        for f in files:
            fullpath = os.path.join(thisdir, f)
            newfile = '{0}.{1}'.format(fullpath, args['compress'])
            # TODO: add compressed tarball support.
            # However, I can't do this on memory-constrained systems for lrzip.
            # See: https://github.com/kata198/python-lrzip/issues/1
            with open(args['logfile'], 'a') as f:
                f.write('===== {0} Now compressing {1} =====\n'.format(str(datetime.datetime.utcnow()), fullpath))
            if args['compress'].lower() == 'gz':
                import gzip
                with open(fullpath, 'rb') as fh_in, gzip.open(newfile, 'wb') as fh_out:
                    fh_out.writelines(fh_in)
            elif args['compress'].lower() == 'xz':
                import lzma
                with open(fullpath, 'rb') as fh_in, lzma.open(newfile, 'wb', preset = 9|lzma.PRESET_EXTREME) as fh_out:
                    fh_out.writelines(fh_in)
            elif args['compress'].lower() == 'bz2':
                import bz2
                with open(fullpath, 'rb') as fh_in, bz2.open(newfile, 'wb') as fh_out:
                    fh_out.writelines(fh_in)
            elif args['compress'].lower() == 'lrz':
                import lrzip
                with open(fullpath, 'rb') as fh_in, open(newfile, 'wb') as fh_out:
                    fh_out.write(lrzip.compress(fh_in.read()))
            os.remove(fullpath)
            if getpass.getuser() == 'root':
                uid = getpwnam(args['user']).pw_uid
                gid = getgrnam(args['group']).gr_gid
                os.chown(newfile, uid, gid)
    return()

def syncDB(args):
    if not args['rsync']:
        return()
    cmd = ['rsync',
           '-a',
           '--delete',
           os.path.join(args['destdir'], '.'),
           args['rsync']]
    if args['throttle'] > 0.0:
        cmd.insert(-1, '--bwlimit={0}'.format(str(args['throttle'])))
    with open(args['logfile'], 'a') as f:
        f.write('===== {0} Rsyncing to mirror =====\n'.format(str(datetime.datetime.utcnow())))
    with open(args['logfile'], 'a') as f:
        subprocess.run(cmd, stdout = f, stderr = f)
    return()

def parseArgs():
    cfg = getDefaults()
    system = cfg['system']
    paths = cfg['paths']
    sync = cfg['sync']
    runtime = cfg['runtime']
    args = argparse.ArgumentParser(description = 'sksdump - a tool for dumping the SKS Database',
                                   epilog = 'brent s. || 2017 || https://square-r00t.net')
    args.add_argument('-u',
                      '--user',
                      default = system['user'],
                      dest = 'user',
                      help = 'The user that you run SKS services as.')
    args.add_argument('-g',
                      '--group',
                      default = system['group'],
                      dest = 'group',
                      help = 'The group that SKS services run as.')
    args.add_argument('-c',
                      '--compress',
                      default = system['compress'],
                      dest = 'compress',
                      choices = ['xz', 'gz', 'bz2', 'lrz', None],
                      help = 'The compression scheme to apply to the dumps.')
    args.add_argument('-s',
                      '--services',
                      default = system['svcs'],
                      dest = 'svcs',
                      help = 'A comma-separated list of services that will be stopped/started for the dump (in the provided order).')
    args.add_argument('-l',
                      '--log',
                      default = system['logfile'],
                      dest = 'logfile',
                      help = 'The path to the logfile.')
    args.add_argument('-a',
                      '--days',
                      default = system['days'],
                      dest = 'days',
                      type = int,
                      help = 'How many days to keep rotation for.')
    args.add_argument('-d',
                      '--dumpkeys',
                      default = system['dumpkeys'],
                      dest = 'dumpkeys',
                      type = int,
                      help = 'How many keys to put in each dump.')
    args.add_argument('-b',
                      '--basedir',
                      default = paths['basedir'],
                      dest = 'basedir',
                      help = 'The directory which holds your SKS DB.')
    args.add_argument('-e',
                      '--destdir',
                      default = paths['destdir'],
                      dest = 'destdir',
                      help = 'The directory where the dumps should be saved (a sub-directory with the date will be created).')
    args.add_argument('-r',
                      '--rsync',
                      default = paths['rsync'],
                      dest = 'rsync',
                      help = 'The remote (user@host:/path/) or local (/path/) path to use to sync the dumps to.')
    args.add_argument('-t',
                      '--throttle',
                      default = float(sync['throttle']),
                      dest = 'throttle',
                      type = float,
                      help = 'The amount in KiB/s to throttle the rsync to. Use 0 for no throttling.')
    args.add_argument('-D',
                      '--no-dump',
                      dest = 'nodump',
                      action = 'store_true',
                      default = ('nodump' in runtime),
                      help = 'Don\'t dump the SKS DB (default is to dump)')
    args.add_argument('-C',
                      '--no-compress',
                      dest = 'nocompress',
                      action = 'store_true',
                      default = ('nocompress' in runtime),
                      help = 'Don\'t compress the DB dumps (default is to compress)')
    args.add_argument('-S',
                      '--no-sync',
                      dest = 'nosync',
                      action = 'store_true',
                      default = ('nosync' in runtime),
                      help = 'Don\'t sync the dumps to the remote server.')
    varargs = vars(args.parse_args())
    return(varargs)

def main():
    args = parseArgs()
    if getpass.getuser() not in ('root', args['user']):
        exit('ERROR: You must be root or {0}!'.format(args['user']))
    with open(args['logfile'], 'a') as f:
        f.write('===== {0} STARTING =====\n'.format(str(datetime.datetime.utcnow())))
    if not args['nodump']:
        dumpDB(args)
    if not args['nocompress']:
        compressDB(args)
    if not args['nosync']:
        syncDB(args)
    with open(args['logfile'], 'a') as f:
        f.write('===== {0} DONE =====\n'.format(str(datetime.datetime.utcnow())))


if __name__ == '__main__':
    main()
