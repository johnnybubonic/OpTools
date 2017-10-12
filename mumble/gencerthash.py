#!/usr/bin/env python3

import argparse
import getpass
import hashlib
try:
    import OpenSSL  # "python-pyopenssl" package on Arch
except ImportError:
    exit('You need to install PyOpenSSL ("pip3 install --user PyOpenSSL" if pip3 is installed)')
import sys
import os

class Hasher(object):
    def __init__(self, args):
        self.args = args
        self.certChk()
        self.getPass()
        
    def certChk(self):
        self.args['cert'] = os.path.abspath(os.path.expanduser(self.args['cert']))
        if not os.path.lexists(self.args['cert']):
            raise FileNotFoundError('{0} does not exist!'.format(self.args['cert']))
        return()
    
    def getPass(self):
        # Do we need to get the passphrase?
        if self.args['passphrase']:
            if self.args['passphrase'] == 'stdin':
                self.args['passphrase'] = sys.stdin.read().replace('\n', '')
            elif self.args['passphrase'] == 'prompt':
                _repeat = True
                while _repeat == True:
                    _pass_in = getpass.getpass(('\n\033[1mWhat is the encryption password ' +
                                                'for \033[91m{0}\033[0m\033[1m ?\033[0m ').format(self.args['cert']))
                    if not _pass_in or _pass_in == '':
                        print(('\n\033[1mInvalid passphrase for \033[91m{0}\033[0m\033[1m ; ' +
                               'please enter a valid passphrase!\033[0m ').format(self.args['cert']))
                    else:
                        _repeat = False
                        self.args['passphrase'] = _pass_in.replace('\n', '')
                        print()
            else:
                self.args['passphrase'] = None
        return()

    def importCert(self):
        # Try loading the certificate
        try:
            with open(self.args['cert'], 'rb') as f:
                self.pkcs = OpenSSL.crypto.load_pkcs12(f.read(), self.args['passphrase'])
        except OpenSSL.crypto.Error:
            exit('Could not load certificate! (Wrong passphrase?)')
        return()

    def hashCert(self):
        self.crt = self.pkcs.get_certificate()
        self.der = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_ASN1,
                                                   self.crt)
        self.hash = hashlib.sha1(self.der).hexdigest().lower()
        return(self.hash)
        

def parseArgs():
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
    args.add_argument(dest = 'cert',
                      metavar = 'path/to/mumblecert.p12',
                      help = 'The path to your exported Mumble certificate.')
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    cert = Hasher(args)
    cert.importCert()
    h = cert.hashCert()
    print('\n\t\033[1mYour certificate\'s public hash is: \033[94m{0}\033[0m'.format(h))
    print('\n\t\033[1mPlease provide this to the Mumble server administrator that has requested it.\033[0m')

if __name__ == '__main__':
    main()