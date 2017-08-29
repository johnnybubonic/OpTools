#!/usr/bin/env python3

import argparse
import datetime
import email
import os
import re
import shutil
import subprocess
from io import BytesIO
from socket import *
import urllib.parse
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
    keys = {}
    allkeys = []
    # Do we have the key already? If not, fetch.
    for k in args['rcpts'].keys():
        if args['rcpts'][k]['type'] == 'fpr':
            allkeys.append(k)
        if args['rcpts'][k]['type'] == 'email':
            # We need to actually do a lookup on the email address.
            with open(os.devnull, 'w') as f:
                keyout = subprocess.run(['gpg2',
                                        '--search-keys',
                                        '--with-colons',
                                        '--batch',
                                        k],
                                        stdout = subprocess.PIPE,
                                        stderr = f)
            keyout = keyout.stdout.decode('utf-8').splitlines()
            for line in keyout:
                if line.startswith('pub:'):
                    key = line.split(':')[1]
                    keys[key] = {}
                    keys[key]['uids'] = {}
                    keys[key]['time'] = int(line.split(':')[4])
                elif line.startswith('uid:'):
                    uid = re.split('<(.*)>', urllib.parse.unquote(line.split(':')[1].strip()))
                    uid.remove('')
                    uid = [u.strip() for u in uid]
                    keys[key]['uids'][uid[1]] = {}
                    keys[key]['uids'][uid[1]]['comment'] = uid[0]
                    keys[key]['uids'][uid[1]]['time'] = int(line.split(':')[2])
            if len(keys) > 1:                # Print the keys and prompt for a selection.
                print('\nWe found the following keys for <{0}>...\n\nKEY ID:'.format(k))
                for k in keys:
                    print('{0}\n{1:6}(Generated at {2})  UIDs:'.format(k, '', datetime.datetime.utcfromtimestamp(keys[k]['time'])))
                    for email in keys[k]['uids']:
                        print('{0:42}(Generated {3}) <{2}> {1}'.format('',
                                                                          keys[k]['uids'][email]['comment'],
                                                                          email,
                                                                          datetime.datetime.utcfromtimestamp(
                                                                              keys[k]['uids'][email]['time'])))
                    print()
                while True:
                    key = input('Please enter the (full) appropriate key: ')
                    if key not in keys.keys():
                        print('Please enter a full key ID from the list above or hit ctrl-d to exit.')
                    else:
                        allkeys.append(key)
                        break
            else:
                if not len(keys.keys()) >= 1:
                    print('Could not find {0}!'.format(k))
                    continue
                key = list(keys.keys())[0]
                print('\nFound key {0} for <{1}> (Generated at {2}):'.format(key, k, datetime.datetime.utcfromtimestamp(keys[key]['time'])))
                for email in keys[key]['uids']:
                    print('\t(Generated {2}) {0} <{1}>'.format(keys[key]['uids'][email]['comment'],
                                              email,
                                              datetime.datetime.utcfromtimestamp(keys[key]['uids'][email]['time'])))
                allkeys.append(key)
                print()
    ## And now we can (FINALLY) fetch the key(s).
    recvcmd = ['gpg2', '--recv-keys', '--batch']  # We'll add the keys onto the end of this next.
    recvcmd.extend(allkeys)
    with open(os.devnull, 'w') as f:
        subprocess.run(recvcmd, stdout = f, stderr = f)  # We hide stderr because gpg, for some unknown reason, spits non-errors to stderr.
    return(allkeys)

def modifyDirmngr(op, args):
    if not args['keyservers']:
        return()
    pid = str(os.getpid())
    activecfg = os.path.join(args['gpgdir'], 'dirmngr.conf')
    bakcfg = '{0}.{1}'.format(activecfg, pid)
    if op in ('new', 'start'):
        if os.path.lexists(activecfg):
            shutil.copy2(activecfg, bakcfg)
        with open(bakcfg, 'r') as read, open(activecfg, 'w') as write:
            for line in read:
                if not line.startswith('keyserver '):
                    write.write(line)
        with open(activecfg, 'a') as f:
            for s in args['keyservers']:
                uri = '{0}://{1}:{2}'.format(s['proto'], s['server'], s['port'][0])
                f.write('keyserver {0}\n'.format(uri))
    if op in ('old', 'stop'):
        if os.path.lexists(bakcfg):
            with open(bakcfg, 'r') as read, open(activecfg, 'w') as write:
                for line in read:
                    write.write(line)
            os.remove(bakcfg)
        else:
            os.remove(activecfg)
    subprocess.run(['gpgconf',
                    '--reload',
                    'dirmngr'])
    return()

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
    urlobj = urllib.parse.urlparse(uri)
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
                                                                                                        defkeyservers))
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
            if not re.match('^[\w\.\+\-]+\@[\w-]+\.[a-z]{2,3}$', k):  # is it an email address?
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
    modifyDirmngr('new', args)
    getKeys(args)
    modifyDirmngr('old', args)

if __name__ == '__main__':
    main()
