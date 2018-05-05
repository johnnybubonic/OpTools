#!/usr/bin/env python3

# Thanks to Matt Rude and https://gist.github.com/mattrude/b0ac735d07b0031bb002 so I can know what the hell I'm doing.

import argparse
import base64
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
                      'rsync': ('root@mirror.square-r00t.net:' +
                                '/srv/http/sks/dumps'),
                      'sksbin': '/usr/bin/sks'},
            'runtime': {'nodump': None, 'nocompress': None, 'nosync': None}}
    ## Build out the default .ini.
    dflt_b64 = ("""IyBJTVBPUlRBTlQ6IFRoaXMgc2NyaXB0IHVzZXMgY2VydGFpbiBwZXJtaXNz
                   aW9ucyBmdW5jdGlvbnMgdGhhdCByZXF1aXJlIHNvbWUKIyBmb3JldGhvdWdo
                   dC4KIyBZb3UgY2FuIGVpdGhlciBydW4gYXMgcm9vdCwgd2hpY2ggaXMgdGhl
                   ICJlYXN5IiB3YXksIE9SIHlvdSBjYW4gcnVuIGFzIHRoZQojIHNrcyB1c2Vy
                   IChvci4uLiB3aGF0ZXZlciB1c2VyIHlvdXIgU0tTIGluc3RhbmNlIHJ1bnMg
                   YXMpLgojIEl0IGhhcyB0byBiZSBvbmUgb3IgdGhlIG90aGVyOyB5b3UnbGwg
                   U0VSSU9VU0xZIG1lc3MgdGhpbmdzIHVwIG90aGVyd2lzZS4KIyBJZiB5b3Ug
                   cnVuIGFzIHRoZSBza3MgdXNlciwgTUFLRSBTVVJFIHRoZSBmb2xsb3dpbmcg
                   aXMgc2V0IGluIHlvdXIgc3Vkb2VycwojICh3aGVyZSBTS1NVU0VSIGlzIHRo
                   ZSB1c2VybmFtZSBza3MgcnVucyBhcyk6CiMJQ21uZF9BbGlhcyBTS1NDTURT
                   ID0gL3Vzci9iaW4vc3lzdGVtY3RsIHN0YXJ0IHNrcy1kYixcCiMJICAgICAg
                   ICAgICAgICAgICAgICAgL3Vzci9iaW4vc3lzdGVtY3RsIHN0b3Agc2tzLWRi
                   LFwKIyAgICAgICAgICAgICAgICAgICAgICAgIC91c3IvYmluL3N5c3RlbWN0
                   bCBzdGFydCBza3MtcmVjb24sXAojCQkgICAgICAgICAgICAgICAgIC91c3Iv
                   YmluL3N5c3RlbWN0bCBzdG9wIHNrcy1yZWNvbgojCVNLU1VTRVIgQUxMID0g
                   Tk9QQVNTV0Q6IFNLU0NNRFMKCiMgVGhpcyB3YXMgd3JpdHRlbiBmb3Igc3lz
                   dGVtZCBzeXN0ZW1zIG9ubHkuIFR3ZWFraW5nIHdvdWxkIGJlIG5lZWRlZCBm
                   b3IKIyBub24tc3lzdGVtZCBzeXN0ZW1zIChzaW5jZSBldmVyeSBub24tc3lz
                   dGVtZCB1c2VzIHRoZWlyIG93biBpbml0IHN5c3RlbQojIGNhbGxhYmxlcy4u
                   LikKCiMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMj
                   IyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMKCiMgVGhp
                   cyBzZWN0aW9uIGNvbnRyb2xzIHZhcmlvdXMgc3lzdGVtIGNvbmZpZ3VyYXRp
                   b24uCltzeXN0ZW1dCgojIFRoaXMgc2hvdWxkIGJlIHRoZSB1c2VyIFNLUyBy
                   dW5zIGFzLgp1c2VyID0gc2tzCgojIFRoaXMgaXMgdGhlIGdyb3VwIHRoYXQg
                   U0tTIHJ1bnMgYXMuCmdyb3VwID0gc2tzCgojIElmIGVtcHR5LCBkb24ndCBj
                   b21wcmVzcyBkdW1wcy4KIyBJZiBvbmUgb2Y6IHh6LCBneiwgYnoyLCBvciBs
                   cnogKGZvciBscnppcCkgdGhlbiB1c2UgdGhhdCBjb21wcmVzc2lvbiBhbGdv
                   LgojIE5vdGUgdGhhdCBscnppcCByZXF1aXJlcyBleHRyYSBpbnN0YWxsYXRp
                   b24uCmNvbXByZXNzID0geHoKCiMgVGhlc2Ugc2VydmljZXMgd2lsbCBiZSBz
                   dG9wcGVkL3N0YXJ0ZWQsIGluIG9yZGVyLCBiZWZvcmUvYWZ0ZXIgZHVtcHMu
                   IElmIG1vcmUKIyB0aGFuIG9uZSwgc2VwZXJhdGUgYnkgY29tbWFzLgpzdmNz
                   ID0gc2tzLWRiLHNrcy1yZWNvbgoKIyBUaGUgcGF0aCB0byB0aGUgbG9nZmls
                   ZS4KbG9nZmlsZSA9IC92YXIvbG9nL3Nrc2R1bXAubG9nCgojIFRoZSBudW1i
                   ZXIgb2YgZGF5cyBvZiByb3RhdGVkIGtleSBkdW1wcy4gSWYgZW1wdHksIGRv
                   bid0IHJvdGF0ZS4KZGF5cyA9IDEKCiMgSG93IG1hbnkga2V5cyB0byBpbmNs
                   dWRlIGluIGVhY2ggZHVtcCBmaWxlLgpkdW1wa2V5cyA9IDE1MDAwCgoKIyBU
                   aGlzIHNlY3Rpb24gY29udHJvbHMgc3luYyBzZXR0aW5ncy4KW3N5bmNdCgoj
                   IFRoaXMgc2V0dGluZyBpcyB3aGF0IHRoZSBzcGVlZCBzaG91bGQgYmUgdGhy
                   b3R0bGVkIHRvLCBpbiBLaUIvcy4gSWYgZW1wdHkgb3IKIyAwLCBwZXJmb3Jt
                   IG5vIHRocm90dGxpbmcuCnRocm90dGxlID0gMAoKCiMgVGhpcyBzZWN0aW9u
                   IGNvbnRyb2xzIHdoZXJlIHN0dWZmIGdvZXMgYW5kIHdoZXJlIHdlIHNob3Vs
                   ZCBmaW5kIGl0LgpbcGF0aHNdCgojIFdoZXJlIHlvdXIgU0tTIERCIGlzLgpi
                   YXNlZGlyID0gL3Zhci9saWIvc2tzCgojIFRoaXMgaXMgdGhlIGJhc2UgZGly
                   ZWN0b3J5IHdoZXJlIHRoZSBkdW1wcyBzaG91bGQgZ28uCiMgVGhlcmUgd2ls
                   bCBiZSBhIHN1Yi1kaXJlY3RvcnkgY3JlYXRlZCBmb3IgZWFjaCBkYXRlLgpk
                   ZXN0ZGlyID0gL3Nydi9odHRwL3Nrcy9kdW1wcwoKIyBUaGUgcGF0aCBmb3Ig
                   cnN5bmNpbmcgdGhlIGR1bXBzLiBJZiBlbXB0eSwgZG9uJ3QgcnN5bmMuCnJz
                   eW5jID0gcm9vdEBtaXJyb3Iuc3F1YXJlLXIwMHQubmV0Oi9zcnYvaHR0cC9z
                   a3MvZHVtcHMKCiMgVGhlIHBhdGggdG8gdGhlIHNrcyBiaW5hcnkgdG8gdXNl
                   Lgpza3NiaW4gPSAvdXNyL2Jpbi9za3MKCgojIFRoaXMgc2VjdGlvbiBjb250
                   cm9scyBydW50aW1lIG9wdGlvbnMuIFRoZXNlIGNhbiBiZSBvdmVycmlkZGVu
                   IGF0IHRoZQojIGNvbW1hbmRsaW5lLiBUaGV5IHRha2Ugbm8gdmFsdWVzOyB0
                   aGV5J3JlIG1lcmVseSBvcHRpb25zLgpbcnVudGltZV0KCiMgRG9uJ3QgZHVt
                   cCBhbnkga2V5cy4KIyBVc2VmdWwgZm9yIGRlZGljYXRlZCBpbi10cmFuc2l0
                   L3ByZXAgYm94ZXMuCjtub2R1bXAKCiMgRG9uJ3QgY29tcHJlc3MgdGhlIGR1
                   bXBzLCBldmVuIGlmIHdlIGhhdmUgYSBjb21wcmVzc2lvbiBzY2hlbWUgc3Bl
                   Y2lmaWVkIGluCiMgdGhlIFtzeXN0ZW06Y29tcHJlc3NdIHNlY3Rpb246ZGly
                   ZWN0aXZlLgo7bm9jb21wcmVzcwoKIyBEb24ndCBzeW5jIHRvIGFub3RoZXIg
                   c2VydmVyL3BhdGgsIGV2ZW4gaWYgb25lIGlzIHNwZWNpZmllZCBpbiBbcGF0
                   aHM6cnN5bmNdLgo7bm9zeW5j""")
    realcfg = configparser.ConfigParser(defaults = dflt, allow_no_value = True)
    if not os.path.isfile(cfgfile):
        with open(cfgfile, 'w') as f:
            f.write(base64.b64decode(dflt_b64).decode('utf-8'))
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
        # we COULD set it as part of the os.makedirs, but iirc it doesn't set
        # it for existing dirs.
        for d in (args['destdir'], nowdir):
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
    cmd = [args['sksbin'],
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
    # I use os.walk here because we might handle this differently in the
    # future...
    for thisdir, dirs, files in os.walk(curdir):
        files.sort()
        for f in files:
            fullpath = os.path.join(thisdir, f)
            newfile = '{0}.{1}'.format(fullpath, args['compress'])
            # TODO: add compressed tarball support.
            # However, I can't do this on memory-constrained systems for lrzip.
            # See: https://github.com/kata198/python-lrzip/issues/1
            with open(args['logfile'], 'a') as f:
                f.write('===== {0} Now compressing {1} =====\n'.format(
                                            str(datetime.datetime.utcnow()),
                                                                    fullpath))
            if args['compress'].lower() == 'gz':
                import gzip
                with open(fullpath, 'rb') as fh_in, gzip.open(newfile,
                                                              'wb') as fh_out:
                    fh_out.writelines(fh_in)
            elif args['compress'].lower() == 'xz':
                import lzma
                with open(fullpath, 'rb') as fh_in, \
                        lzma.open(newfile,
                                  'wb',
                                  preset = 9|lzma.PRESET_EXTREME) as fh_out:
                    fh_out.writelines(fh_in)
            elif args['compress'].lower() == 'bz2':
                import bz2
                with open(fullpath, 'rb') as fh_in, bz2.open(newfile,
                                                             'wb') as fh_out:
                    fh_out.writelines(fh_in)
            elif args['compress'].lower() == 'lrz':
                import lrzip
                with open(fullpath, 'rb') as fh_in, open(newfile,
                                                         'wb') as fh_out:
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
        f.write('===== {0} Rsyncing to mirror =====\n'.format(
                                            str(datetime.datetime.utcnow())))
    with open(args['logfile'], 'a') as f:
        subprocess.run(cmd, stdout = f, stderr = f)
    return()

def parseArgs():
    cfg = getDefaults()
    system = cfg['system']
    paths = cfg['paths']
    sync = cfg['sync']
    runtime = cfg['runtime']
    args = argparse.ArgumentParser(description = ('sksdump - a tool for ' +
                                                  'dumping an SKS Database'),
                                   epilog = ('brent s. || 2018 || ' +
                                             'https://square-r00t.net'))
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
                      help = ('A comma-separated list of services that will ' +
                              'be stopped/started for the dump (in the ' +
                              'provided order).'))
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
    args.add_argument('-x',
                      '--sks-binary',
                      default = paths['sksbin'],
                      dest = 'sksbin',
                      help = ('The path to the SKS binary/executable to use ' +
                              'to perform the dump.'))
    args.add_argument('-e',
                      '--destdir',
                      default = paths['destdir'],
                      dest = 'destdir',
                      help = ('The directory where the dumps should be ' +
                              'saved (a sub-directory with the date will be ' +
                              'created).'))
    args.add_argument('-r',
                      '--rsync',
                      default = paths['rsync'],
                      dest = 'rsync',
                      help = ('The remote (user@host:/path/) or local '+
                              '(/path/) path to use to sync the dumps to.'))
    args.add_argument('-t',
                      '--throttle',
                      default = float(sync['throttle']),
                      dest = 'throttle',
                      type = float,
                      help = ('The amount in KiB/s to throttle the rsync ' +
                              'to. Use 0 for no throttling.'))
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
                      help = ('Don\'t compress the DB dumps (default is to ' +
                              'compress)'))
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
        f.write('===== {0} STARTING =====\n'.format(
                                            str(datetime.datetime.utcnow())))
    if not args['nodump']:
        dumpDB(args)
    if not args['nocompress']:
        compressDB(args)
    if not args['nosync']:
        syncDB(args)
    with open(args['logfile'], 'a') as f:
        f.write('===== {0} DONE =====\n'.format(
                                            str(datetime.datetime.utcnow())))
    with open(os.path.join(args['destdir'], 'LAST_COMPLETED_DUMP.txt'),
              'w') as f:
        f.write(str(datetime.datetime.utcnow()))


if __name__ == '__main__':
    main()
