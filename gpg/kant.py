#!/usr/bin/env python3

import argparse
import datetime
import email
import os
import re
import subprocess
from io import BytesIO
from socket import *
from urllib.parse import urlparse
import gpgme  # non-stdlib; Arch package is "python-pygpgme"

# TODO:
# -a --batch arg, with filename parameter. needs to contain keyID or email address and trust level
# -attach my pubkey
# mail to first email address in key with signed message:
#Subj: Your GPG key has been signed
#
#Hello! Thank you for participating in a keysigning party and exchanging keys.
#
#I have signed your key (KEYID) with trust level "TRUSTLEVEL" because:
#
#* You have presented sufficient proof of identity
#
#The signatures have been pushed to the pgp.mit.edu and hkps.pool.sks-keyservers.net keyservers.
#
#I have taken the liberty of attaching my public key in the event you've not signed it yet and were unable to find it. Please feel free to push to pgp.mit.edu or hkps.pool.sks-keyservers.net.
#
#As a reminder, my key ID, Keybase.io username, and verification/proof of identity can all be found at:
#
#https://devblog.square-r00t.net/about/my-gpg-public-key-verification-of-identity
#
#Thanks again!

def getKeys(args):
    # Get our concept
    os.environ['GNUPGHOME'] = args['gpgdir']
    gpg = gpgme.Context()
    # Do we have the key already? If not, fetch.
    for k in args['rcpts'].keys():
        if args['rcpts'][k]['type'] == 'fpr':
            # It's a key ID.
            pass
        elif args['rcpts'][k]['type'] == 'email':
            # We need to actually do a lookup on the email address.
            pass
    return(gpg)

def serverParser(uri):
    # https://en.wikipedia.org/wiki/Key_server_(cryptographic)#Keyserver_examples
    # We need to make a mapping of the default ports.
    server = {}
    protos = {'hkp': [11371, ['tcp', 'udp']],
              'hkps': [443, ['tcp']],  # Yes, same as https
              'http': [80, ['tcp']],
              'https': [443, ['tcp']],  # SSL/TLS
              'ldap': [389, ['tcp', 'udp']],  # includes TLS negotiation since it runs on the same port
              'ldaps': [636, ['tcp', 'udp']]}  # SSL
    urlobj = urlparse(uri)
    server['proto'] = urlobj.scheme
    lazy = False
    if not server['proto']:
        server['proto'] = 'hkp'  # Default
    server['server'] = urlobj.hostname
    if not server['server']:
        server['server'] = re.sub('^([A-Za-z]://)?(.+[^:][^0-9])(:[0-9]+)?$', '\g<2>', uri)
        lazy = True
    server['port'] = urlobj.port
    if not server['port']:
        if lazy:
            p = re.sub('.*:([0-9]+)$', '\g<1>', uri)
    server['port'] = protos[server['proto']]  # Default
    return(server)

def parseArgs():
    def getDefGPGDir():
        try:
            gpgdir = os.environ['GNUPGHOME']
        except KeyError:
            try:
                homedir = os.environ['HOME']
                gpgdchk = os.path.join(homedir, '.gnupg')
            except KeyError:
                # There is no reason that this should ever get this far, but... edge cases be crazy.
                gpgdchk = os.path.join(os.path.expanduser('~'), '.gnupg')
            if os.path.isdir(gpgdchk):
                gpgdir = gpgdchk
            else:
                gpgdir = None
        return(gpgdir)
    def getDefKey(defgpgdir):
        os.environ['GNUPGHOME'] = defgpgdir
        if not defgpgdir:
            return(None)
        defkey = None
        gpg = gpgme.Context()
        for k in gpg.keylist(None, True):  # params are query and secret keyring, respectively
            if k.can_sign and True not in (k.revoked, k.expired, k.disabled):
                defkey = k.subkeys[0].fpr
                break  # We'll just use the first primary key we find that's valid as the default.
        return(defkey)
    def getDefKeyservers(defgpgdir):
        srvlst = [None]
        # We don't need these since we use the gpg agent. Requires GPG 2.1 and above, probably.
        #if os.path.isfile(os.path.join(defgpgdir, 'dirmngr.conf')):
        #    pass
        dirmgr_out = subprocess.run(['gpg-connect-agent', '--dirmngr', 'keyserver', '/bye'], stdout = subprocess.PIPE)
        for l in dirmgr_out.stdout.decode('utf-8').splitlines():
            #if len(l) == 3 and l.lower().startswith('s keyserver'):  # It's a keyserver line
            if l.lower().startswith('s keyserver'):  # It's a keyserver line
                s = l.split()[2]
                if len(srvlst) == 1 and srvlst[0] == None:
                    srvlst = [s]
                else:
                    srvlst.append(s)
        return(','.join(srvlst))
    defgpgdir = getDefGPGDir()
    defkey = getDefKey(defgpgdir)
    defkeyservers = getDefKeyservers(defgpgdir)
    args = argparse.ArgumentParser(description = 'Keysigning Assistance and Notifying Tool (KANT)',
                                   epilog = 'brent s. || 2017 || https://square-r00t.net')
    args.add_argument('-k',
                      '--keys',
                      dest = 'keys',
                      required = True,
                      help = 'A single or comma-separated list of keys to sign, trust, and notify. Can also be an email address.')
    args.add_argument('-K',
                      '--sigkey',
                      dest = 'sigkey',
                      default = defkey,
                      help = 'The key to use when signing other keys. Default is \033[1m{0}\033[0m.'.format(defkey))
    args.add_argument('-d',
                      '--gpgdir',
                      dest = 'gpgdir',
                      default = defgpgdir,
                      help = 'The GnuPG configuration directory to use (containing your keys, etc.). Default is \033[1m{0}\033[0m.'.format(defgpgdir))
    args.add_argument('-s',
                      '--keyservers',
                      dest = 'keyservers',
                      default = defkeyservers,
                      help = 'The comma-separated keyserver(s) to push to. If "None", don\'t push signatures. Default is \033[1m{0}\033[0m.'.format(
                                                                                                        ','.join(
                                                                                                                 defkeyservers)))
    args.add_argument('-n',
                      '--netproto',
                      dest = 'netproto',
                      action = 'store',
                      choices = ['4', '6'],
                      default = '4',
                      help = 'Whether to use (IPv)4 or (IPv)6. Default is to use IPv4.')
    args.add_argument('-t',
                      '--testkeyservers',
                      dest = 'testkeyservers',
                      action = 'store_true',
                      help = 'If specified, initiate a test connection with each keyserver before anything else. Disabled by default.')
    return(args)

def verifyArgs(args):
    ## Some pythonization...
    # We don't want to only strip the values, we want to remove ALL whitespace. 
    #args['keys'] = [k.strip() for k in args['keys'].split(',')]
    #args['keyservers'] = [s.strip() for s in args['keyservers'].split(',')]
    args['keys'] = [re.sub('\s', '', k) for k in args['keys'].split(',')]
    args['keyservers'] = [re.sub('\s', '', s) for s in args['keyservers'].split(',')]
    args['keyservers'] = [serverParser(s) for s in args['keyservers']]
    ## Key(s) to sign
    args['rcpts'] = {}
    for k in args['keys']:
        args['rcpts'][k] = {}
        try:
            int(k, 16)
            ktype = 'fpr'
        except:  # If it isn't a valid key ID...
            if not re.match('^[\w\.\+\-]+\@[\w]+\.[a-z]{2,3}$', k):  # is it an email address?
                raise ValueError('{0} is not a valid email address'.format(k))
            else:
                ktype = 'email'
        args['rcpts'][k]['type'] = ktype
        if ktype == 'fpr' and not len(k) == 40:  # Security is important. We don't want users getting collisions, so we don't allow shortened key IDs.
            raise ValueError('{0} is not a full 40-char key ID or key fingerprint'.format(k))
    del args['keys']
    ## Signing key
    if not args['sigkey']:
        raise ValueError('A key for signing is required') # We need a key we can sign with.
    else:
        if not os.path.lexists(args['gpgdir']):
            raise FileNotFoundError('{0} does not exist'.format(args['gpgdir']))
        elif os.path.isfile(args['gpgdir']):
            raise NotADirectoryError('{0} is not a directory'.format(args['gpgdir']))
        try:
            os.environ['GNUPGHOME'] = args['gpgdir']
            gpg = gpgme.Context()
        except:
            raise RuntimeError('Could not use {0} as a GnuPG home'.format(args['gpgdir']))
        # Now we need to verify that the private key exists...
        try:
            sigkey = gpg.get_key(args['sigkey'], True)
        except GpgmeError:
            raise ValueError('Cannot use key {0}'.format(args['sigkey']))
        # And that it is an eligible candidate to use to sign.
        if not sigkey.can_sign or True in (sigkey.revoked, sigkey.expired, sigkey.disabled):
            raise ValueError('{0} is not a valid candidate for signing'.format(args['sigkey']))
    ## Keyservers
    if args['testkeyservers']:
        for s in args['keyservers']:
            # Test to make sure the keyserver is accessible.
            # First we need to construct a way to use python's socket connector
            # Great. Now we need to just quickly check to make sure it's accessible - if specified.
            if args['netproto'] == '4':
                nettype = AF_INET
            elif args['netproto'] == '6':
                nettype = AF_INET6
            for proto in s['port'][1]:
                if proto == 'udp':
                    netproto = SOCK_DGRAM
                elif proto == 'tcp':
                    netproto = SOCK_STREAM
                sock = socket(nettype, netproto)
                sock.settimeout(10)
                tests = sock.connect_ex((s['server'], int(s['port'][0])))
                uristr = '{0}://{1}:{2} ({3})'.format(s['proto'], s['server'], s['port'][0], proto.upper())
                if not tests == 0:
                    raise RuntimeError('Keyserver {0} is not available'.format(uristr))
                else:
                    print('Keyserver {0} is accepting connections.'.format(uristr))
                sock.close()
    return(args)

def main():
    rawargs = parseArgs()
    args = verifyArgs(vars(rawargs.parse_args()))
    import pprint
    pprint.pprint(args)
    getKeys(args)

if __name__ == '__main__':
    main()
