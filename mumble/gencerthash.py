#!/usr/bin/env python3

# TODO: can we use struct instead for blobParser?

import argparse
import getpass
import hashlib
import re
import sys
import os
from collections import defaultdict
try:
    import OpenSSL  # "python-pyopenssl" package on Arch
except ImportError:
    exit('You need to install PyOpenSSL ("pip3 install --user PyOpenSSL" if pip3 is installed)')

## DEFINE SOME PRETTY STUFF ##
class color(object):
    # Windows doesn't support ANSI color escapes like sh does.
    if sys.platform == 'win32':
        # "You should be using subprocess!" yeah yeah yeah, I know, shut up.
        # I already have OS imported and this is a quick hack.
        BLACK = os.system('color 0')
        BLUE = os.system('color 1')
        GREEN = os.system('color 2')
        DARKCYAN = os.system('color 3')  # "Aqua" text
        RED = os.system('color 4')
        PURPLE = os.system('color 5')
        YELLOW = os.system('color 6')
        END = os.system('color 7')  # "White" text
        GRAY = os.system('color 8')
        CYAN = os.system('color 9') # "Light Blue" text
        LTGREEN = os.system('color A')  # "Light Green" text
        LTAQUA = os.system('color B')  # "Light Aqua" text
        LTRED = os.system('color C')  # "Light Red" text
        LTPURPLE = os.system('color D')  # "Light Purple" text
        LTYELLOW = os.system('color E')  # "Light Yellow" text
        BOLD = os.system('color F')  # "Bright White" text
        UNDERLINE = None
    else:
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

class Hasher(object):
    def __init__(self, args):
        self.args = args
        self.blobGetter(self.args['cert'])
        self.blobParser()

    def getPass(self):
        # Do we need to get the passphrase?
        if self.args['passphrase']:
            if self.args['passphrase'] == 'stdin':
                self.args['passphrase'] = sys.stdin.read().replace('\n', '')
            elif self.args['passphrase'] == 'prompt':
                _colorargs = (color.BOLD, color.RED, self.args['cert'], color.END)
                _repeat = True
                while _repeat == True:
                    _pass_in = getpass.getpass(('\n{0}What is the encryption password ' +
                                                'for {1}{2}{0}{3}{0} ?{3} ').format(*_colorargs))
                    if not _pass_in or _pass_in == '':
                        print(('\n{0}Invalid passphrase for {1}{2}{0}{3}{0} ; ' +
                               'please enter a valid passphrase!{3} ').format(*_colorargs))
                    else:
                        _repeat = False
                        self.args['passphrase'] = _pass_in.replace('\n', '')
                        print()
            else:
                self.args['passphrase'] = None
        return()

    def importCert(self):
        self.getPass()
        # Try loading the certificate
        try:
            self.pkcs = OpenSSL.crypto.load_pkcs12(self.cert, self.args['passphrase'])
        except OpenSSL.crypto.Error:
            exit('Could not load certificate! (Wrong passphrase? Wrong file?)')
        return()

    def hashCert(self):
        self.crt_in = self.pkcs.get_certificate()
        self.der = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_ASN1,
                                                   self.crt_in)
        self.hash = hashlib.sha1(self.der).hexdigest().lower()
        return(self.hash)

    def blobGetter(self, blobpath):
        self.cert = None
        self.blob = None
        _blst = blobpath.split(':')
        if len(_blst) == 2:
            blob = _blst[1]
            self.certtype = _blst[0].lower()
        elif len(_blst) == 1:
            blob = _blst[0]
            self.certtype = 'file'
        else:
            raise ValueError('{0} is not a supported path'.format(blobpath))
            self.certtype = None
        if self.certtype:
            _hexblob = None
            if self.certtype in ('plist', 'ini', 'file'):
                blob = os.path.abspath(os.path.expanduser(blob))
                if not os.path.isfile(blob):
                    raise FileNotFoundError('{0} does not exist'.format(blob))
            if self.certtype == 'reg':  # Only supported on Windows machines, obviously.
                if sys.platform == 'win32':
                    import winreg
                elif sys.platform == 'cygwin':
                    # https://bitbucket.org/sfllaw/cygwinreg/issues/5/support-python3
                    exit(('Python 3 under Cygwin does not support reading the registry. ' +
                          'Please use native-Windows Python 3 (for now) or ' +
                          'specify an actual PKCS #12 certificate file.'))
                    #try:
                    #    import cygwinreg as winreg
                    #except ImportError:
                    #    exit('You must install the cygwinreg python module in your cygwin environment to read the registry.')
                _keypath = blob.split('\\')
                _hkey = getattr(winreg, _keypath[0])
                _skeypath = _keypath[1:-1]
                _ckey = _keypath[-1]
                _r = winreg.OpenKey(_hkey, '\\'.join(_skeypath))
                _hexblob, _ = winreg.QueryValueEx(_r, _ckey)
                winreg.CloseKey(_r)
            elif self.certtype == 'plist':  # plistlib, however, is thankfully cross-platform.
                import plistlib
                with open(blob, 'rb') as f:
                    _pdata = plistlib.loads(f.read())
                    _hexblob = _pdata['net.certificate']
            elif self.certtype == 'ini':
                import configparser
                _parser = configparser.RawConfigParser()
                _parser.read(blob)
                _cfg = defaultdict(dict)
                for s in _parser.sections():
                    _cfg[s] = {}
                    for k in _parser.options(s):
                        _cfg[s][k] = _parser.get(s, k)
                self.blob = _cfg['net']['certificate']
            else:  # It's (supposedly) a PKCS #12 file - obviously, cross-platform.
                with open(blob, 'rb') as f:
                    self.cert = f.read()
        return()

    def blobParser(self):
        if not self.blob:
            return()
        if self.blob == '':
            raise ValueError('We could not find an embedded certificate.')
        # A pox upon the house of Mumble for not using base64. A POX, I SAY.
        # So instead we need to straight up de-byte-array the mess.
        # The below is an eldritch horror, bound to twist the mind of any sane man
        # into the depths of madness.
        # I probably might have been able to use a struct here, but meh.
        blob = re.sub('^"?@ByteArray\(0(.*)\)"?$',
                      '\g<1>',
                      self.blob,
                      re.MULTILINE, re.DOTALL)
        _bytes = b'0'
        for s in blob.split('\\x'):
            if s == '':
                continue
            _chunk = list(s)
            # Skip the first two chars for string interpolation - they're hex.
            _start = 2
            try:
                _hex = ''.join(_chunk[0:2])
                _bytes += bytes.fromhex(_hex)
            except ValueError:
                # We need to zero-pad, and alter the starting index
                # because yep, you guessed it - their bytearray hex vals
                # (in plaintext) aren't zero-padded, either.
                _hex = ''.join(_chunk[0]).zfill(2)
                _bytes += bytes.fromhex(_hex)
                _start = 1
            # And then append the rest as-is. "Mostly."
            # Namely, we need to change the single-digit null byte notation
            # to actual python null bytes, and then de-escape the escapes.
            # (i.e. '\t' => '   ')
            _str = re.sub('\\\\0([^0])',
                          '\00\g<1>',
                          ''.join(_chunk[_start:])).encode('utf-8').decode('unicode_escape')
            _bytes += _str.encode('utf-8')
            self.cert = _bytes
        return()

def parseArgs():
    # Set the default cert path
    _certpath = '~/Documents/MumbleAutomaticCertificateBackup.p12'
    # This catches ALL versions of macOS/OS X.
    if sys.platform == 'darwin':
        _cfgpath = 'PLIST:~/Library/Preferences/net.sourceforge.mumble.Mumble.plist'
    # ALL versions of windows, even Win10, on x86. Even 64-bit. I know.
    elif sys.platform == 'win32':
        _cfgpath = r'REG:HKEY_CURRENT_USER\Software\Mumble\Mumble\net\certificate'
    # Some people are sensible.
    if sys.platform == 'cygwin':
        _cfgpath = r'REG:HKEY_CURRENT_USER\Software\Mumble\Mumble\net\certificate'
    elif (sys.platform == 'linux') or (re.match('.*bsd.*', sys.platform)):  # duh
        _cfgpath = 'INI:~/.config/Mumble/Mumble.conf'
    else:
        # WHO KNOWS what we're running on
        _cfgpath = None
    if not os.path.isfile(os.path.abspath(os.path.expanduser(_certpath))):
        _defcrt = _cfgpath
    else:
        _defcrt = 'FILE:{0}'.format(_certpath)
    args = argparse.ArgumentParser()
    args.add_argument('-p',
                      '--passphrase',
                      choices = ['stdin', 'prompt'],
                      dest = 'passphrase',
                      default = None,
                      help = ('The default is to behave as if your certificate does not have ' +
                              'a passphrase attached (as this is Mumble\'s default); however, ' +
                              'if you specify \'stdin\' we will expect the passphrase to be given as a stdin pipe, ' +
                              'if you specify \'prompt\', we will prompt you for a passphrase (it will not be echoed back' +
                              'to the console)'))
    args.add_argument('-c', '--cert',
                      dest = 'cert',
                      default = _defcrt,
                      metavar = 'path/to/mumblecert.p12',
                      help = ('The path to your exported PKCS #12 Mumble certificate. ' +
                              'Special prefixes are ' +
                              '{0} (it is a PKCS #12 file, default), ' +
                              '{1} (it is embedded in a macOS/OS X PLIST file), ' +
                              '{2} (it is a Mumble.conf with embedded PKCS#12), or ' +
                              '{3} (it is a path to a Windows registry object). ' +
                              'Default: {4}').format('{0}FILE{1}'.format(color.BOLD, color.END),
                                                     '{0}PLIST{1}'.format(color.BOLD, color.END),
                                                     '{0}INI{1}'.format(color.BOLD, color.END),
                                                     '{0}REG{1}'.format(color.BOLD, color.END),
                                                     '{0}{1}{2}'.format(color.BOLD, _defcrt, color.END)))
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    cert = Hasher(args)
    cert.importCert()
    h = cert.hashCert()
    print('\n\t\033[1mYour certificate\'s public hash is: \033[94m{0}\033[0m'.format(h))
    print('\n\t\033[1mPlease provide this to the Mumble server administrator that has requested it.\033[0m\n')

if __name__ == '__main__':
    main()
