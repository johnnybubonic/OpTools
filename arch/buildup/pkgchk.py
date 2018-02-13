#!/usr/bin/env python3

import argparse
import configparser
import hashlib
import os
import re
import shlex
import subprocess
import tarfile  # for verifying built PKGBUILDs. We just need to grab <tar>/.PKGINFO, and check: pkgver = <version>
import tempfile
from collections import OrderedDict
from urllib.request import urlopen

class color(object):
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


vcstypes = ('bzr', 'git', 'hg', 'svn')    

class pkgChk(object):
    def __init__(self, pkg):
        # pkg should be a string of a PKGBUILD,
        # not the path to a file.
        self.pkg = pkg
        # The below holds parsed data from the PKGBUILD.
        self.pkgdata = {'pkgver': self.getLex('pkgver', 'var'),
                        '_pkgver': self.getLex('_pkgver', 'var'),
                        'pkgname': self.getLex('pkgname', 'var'),
                        'sources': self.getLex('source', 'array')}

    def getLex(self, attrib, attrtype):
        # Parse the PKGBUILD and return actual values from it.
        # attrtype should be "var" or "array".
        # var returns a string and array returns a list.
        # If the given attrib isn't in the pkgbuild, None is returned.
        # The sources array is special, though - it returns a tuple of:
        # (hashtype, dict) where dict is a mapping of:
        # filename: hash
        # filename2: hash2
        # etc.
        if attrtype not in ('var', 'array'):
            raise ValueError('{0} is not a valid attribute type.'.format(attrib))
        _sums = ('sha512', 'sha384', 'sha256', 'sha1', 'md5')  # in order of preference
        _attrmap = {'var': 'echo ${{{0}}}'.format(attrib),
                    'array': 'echo ${{{}[@]}}'.format(attrib)}
        _tempfile = tempfile.mkstemp(text = True)
        with open(_tempfile[1], 'w') as f:
            f.write(self.pkg)
        _cmd = ['/bin/bash',
                '--restricted', '--noprofile',
                '--init-file', _tempfile[1],
                '-i', '-c', _attrmap[attrtype]]
        with open(os.devnull, 'wb') as devnull:
            _out = subprocess.run(_cmd, env = {'PATH': ''},
                                  stdout = subprocess.PIPE,
                                  stderr = devnull).stdout.decode('utf-8').strip()
        if _out == '':
            os.remove(_tempfile[1])
            return(None)
        if attrtype == 'var':
            os.remove(_tempfile[1])
            return(_out)
        else:  # it's an array
            if attrib == 'source':
                _sources = {}
                _source = shlex.split(_out)
                _sumarr = [None] * len(_source)
                for h in _sums:
                    _cmd[-1] = 'echo ${{{0}[@]}}'.format(h + 'sums')
                    with open(os.devnull, 'wb') as devnull:
                        _out = subprocess.run(_cmd, env = {'PATH': ''},
                                              stdout = subprocess.PIPE,
                                              stderr = devnull).stdout.decode('utf-8').strip()
                    if _out != '':
                        os.remove(_tempfile[1])
                        return(h, OrderedDict(zip(_source, shlex.split(_out))))
                    else:
                        continue
                    # No match for checksums.
                    os.remove(_tempfile[1])
                    return(None, OrderedDict(zip(_source, shlex.split(_out))))
            else:
                os.remove(_tempfile[1])
                return(shlex.split(_out))
            return()
        
    def getURL(self, url):
        with urlopen(url) as http:
            code = http.getcode()
        return(code)
    
    def chkVer(self):
        _separators = []
        # TODO: this is to explicitly prevent parsing
        # VCS packages, so might need some re-tooling in the future.
        if self.pkgdata['pkgname'].split('-')[-1] in vcstypes:
            return(None)
        # transform the current version into a list of various components.
        if not self.pkgdata['pkgver']:
            return(None)
        if self.pkgdata['_pkgver']:
            _cur_ver = self.pkgdata['_pkgver']
        else:
            _cur_ver = self.pkgdata['pkgver']
        # This will catch like 90% of the software versions out there.
        # Unfortunately, it won't catch all of them. I dunno how to
        # handle that quite yet. TODO.
        _split_ver = _cur_ver.split('.')
        _idx = len(_split_ver) - 1
        while _idx >= 0:
            _url = re.sub('^[A-Za-z0-9]+::',
                          '',
                          list(self.pkgdata['sources'].keys())[0])
            _code = self.getURL(_url)
            _idx -= 1

def parseArgs():
    _ini = '~/.config/optools/buildup.ini'
    _defini = os.path.abspath(os.path.expanduser(_ini))
    args = argparse.ArgumentParser()
    args.add_argument('-c', '--config',
                      default = _defini,
                      dest = 'config',
                      help = ('The path to the config file. ' +
                              'Default: {0}{1}{2}').format(color.BOLD,
                                                           _defini,
                                                           color.END))
    args.add_argument('-R', '--no-recurse',
                      action = 'store_false',
                      dest = 'recurse',
                      help = ('If specified, and the path provided is a directory, ' +
                              'do NOT recurse into subdirectories.'))
    args.add_argument('-p', '--path',
                      metavar = 'path/to/dir/or/PKGBUILD',
                      default = None,
                      dest = 'pkgpath',
                      help = ('The path to either a directory containing PKGBUILDs (recursion ' +
                              'enabled - see {0}-R/--no-recurse{1}) ' +
                              'or a single PKGBUILD. Use to override ' +
                              'the config\'s PKG:paths.').format(color.BOLD, color.END)) 
    return(args)

def parsePkg(pkgbuildstr):
    p = pkgChk(pkgbuildstr)
    p.chkVer()
    return()

def iterDir(pkgpath, recursion = True):
    filepaths = []
    if os.path.isfile(pkgpath):
        return([pkgpath])
    if recursion:
        for root, subdirs, files in os.walk(pkgpath):
            for vcs in vcstypes:
                if '.{0}'.format(vcs) in subdirs:
                    subdirs.remove('.{0}'.format(vcs))
            for f in files:
                if 'PKGBUILD' in f:
                    filepaths.append(os.path.join(root, f))
    else:
        for f in os.listdir(pkgpath):
            if 'PKGBUILD' in f:
                filepaths.append(f)
    filepaths.sort()
    return(filepaths)

def parseCfg(cfgfile):
    def getPath(p):
        return(os.path.abspath(os.path.expanduser(p)))
    _defcfg = '[PKG]\npaths = \ntestbuild = no\n[VCS]\n'
    for vcs in vcstypes:
        _defcfg += '{0} = no\n'.format(vcs)
    _cfg = configparser.ConfigParser()
    _cfg._interpolation = configparser.ExtendedInterpolation()
    _cfg.read((_defcfg, cfgfile))
    # We convert to a dict so we can do things like list comprehension.
    cfg = {s:dict(_cfg.items(s)) for s in _cfg.sections()}
    if 'paths' not in cfg['PKG'].keys():
        raise ValueError('You must provide a valid configuration ' +
                          'file with the PKG:paths setting specified and valid.')
    cfg['PKG']['paths'] = sorted([getPath(p.strip()) for p in cfg['PKG']['paths'].split(',')],
                                 reverse = True)
    for p in cfg['PKG']['paths'][:]:
        if not os.path.exists(p):
            print('WARNING: {0} does not exist; skipping...'.format(p))
            cfg['PKG']['paths'].remove(p)
    # We also want to convert these to pythonic True/False
    cfg['PKG']['testbuild'] = _cfg['PKG'].getboolean('testbuild')
    for k in vcstypes:
        cfg['VCS'][k] = _cfg['VCS'].getboolean(k)
    return(cfg)

if __name__ == '__main__':
    args = vars(parseArgs().parse_args())
    if not os.path.isfile(args['config']):
        raise FileNotFoundError('{0} does not exist.'.format(cfg))
    cfg = parseCfg(args['config'])
    if args['pkgpath']:
        args['pkgpath'] = os.path.abspath(os.path.expanduser(args['pkgpath']))
        if os.path.isdir(args['pkgpath']):
            iterDir(args['pkgpath'], recursion = args['recurse'])
        elif os.path.isfile(args['pkgpath']):
            parsePkg(args['pkgpath'])
        else:
            raise FileNotFoundError('{0} does not exist.'.format(args['pkgpath']))
    else:
        files = []
        for p in cfg['PKG']['paths']:
            files.extend(iterDir(p))
        files.sort()
        for p in files:
            with open(p, 'r') as f:
                parsePkg(f.read())