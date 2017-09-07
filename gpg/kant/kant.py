#!/usr/bin/env python3

import argparse
import csv
import datetime
import email
import os
import re
import shutil
import subprocess
from io import BytesIO
from socket import *
import urllib.parse
import gpg  # non-stdlib; Arch package is "python-gpgme" - see
            #   https://git.archlinux.org/svntogit/packages.git/tree/trunk/PKGBUILD?h=packages/gpgme and
            #   https://pypi.python.org/pypi/gpg

# TODO:
# - http://tanguy.ortolo.eu/blog/article9/pgp-signature-infos edit certification level- possible with pygpgme?
# -attach pubkey when sending below email
# mail to first email address in key with signed message:
#Subj: Your GPG key has been signed
#
#Hello! Thank you for participating in a keysigning party and exchanging keys.
#
#I have signed your key (KEYID) with trust level "TRUSTLEVEL" because:
#
#* You have presented sufficient proof of identity
#
#The signatures have been pushed to KEYSERVERS.
#
#I have taken the liberty of attaching my public key in the event you've not signed it yet and were unable to find it.
#Please feel free to push to pgp.mit.edu or hkps.pool.sks-keyservers.net.
#
#As a reminder, my key ID, Keybase.io username, and verification/proof of identity can all be found at:
#
#https://devblog.square-r00t.net/about/my-gpg-public-key-verification-of-identity
#
#Thanks again!

class sigsession(object):
    def __init__(self, args):
        self.args = args

    def getKeys(self):
        # Get our concept
        os.environ['GNUPGHOME'] = self.args['gpgdir']
        ctx = gpg.Context()
        keys = {}
        self.keyids = []
        # Do we have the key already? If not, fetch.
        for k in list(self.args['rcpts']):
            if self.args['rcpts'][k]['type'] == 'fpr':
                self.keyids.append(k)
            if self.args['rcpts'][k]['type'] == 'email':
                # We need to actually do a lookup on the email address.
                with open(os.devnull, 'w') as f:
                    # TODO: replace with gpg.keylist_mode(gpgme.KEYLIST_MODE_EXTERN) and internal mechanisms?
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
                                                                           datetime.datetime.utcfromtimestamp(keys[k]['uids'][email]['time'])))
                        print()
                    while True:
                        key = input('Please enter the (full) appropriate key: ')
                        if key not in keys.keys():
                            print('Please enter a full key ID from the list above or hit ctrl-d to exit.')
                        else:
                            self.keyids.append(key)
                            break
                else:
                    if not len(keys.keys()) >= 1:
                        print('Could not find {0}!'.format(k))
                        del(self.args['rcpts'][k])
                        continue
                    key = list(keys.keys())[0]
                    print('\nFound key {0} for {1} (Generated at {2}):'.format(key, k, datetime.datetime.utcfromtimestamp(keys[key]['time'])))
                    for email in keys[key]['uids']:
                        print('\t(Generated {2}) {0} <{1}>'.format(keys[key]['uids'][email]['comment'],
                                                  email,
                                                  datetime.datetime.utcfromtimestamp(keys[key]['uids'][email]['time'])))
                    self.keyids.append(key)
                    print()
        ## And now we can (FINALLY) fetch the key(s).
        # TODO: replace with gpg.keylist_mode(gpgme.KEYLIST_MODE_EXTERN) and internal mechanisms?
        recvcmd = ['gpg2', '--recv-keys', '--batch', '--yes']  # We'll add the keys onto the end of this next.
        recvcmd.extend(self.keyids)
        with open(os.devnull, 'w') as f:
            fetchout = subprocess.run(recvcmd, stdout = f, stderr = f)  # We hide stderr because gpg, for some unknown reason, spits non-errors to stderr.
        return(self.keyids)

    def trustKeys(self):
        # Map the trust levels to "human" equivalent
        trustmap = {-1: ['never', gpgme.VALIDITY_NEVER], # this is... probably? not ideal, but.
                    0: ['unknown', gpgme.VALIDITY_UNKNOWN],
                    1: ['untrusted', gpgme.VALIDITY_UNDEFINED],
                    2: ['marginal', gpgme.VALIDITY_MARGINAL],
                    3: ['full', gpgme.VALIDITY_FULL],
                    4: ['ultimate', gpgme.VALIDITY_ULTIMATE]}
        locmap = {0: ['no', False],
                   1: ['yes', True]}
        def promptTrust(kinfo):
            for k in list(kinfo):
                if 'trust' not in kinfo[k].keys():
                    trust_lvl = None
                    trust_in = input(('\nWhat trust level should we assign to {0}?\n\t\t\t\t     ({1} <{2}>)' +
                                     '\n\n\t\033[1m-1 = Never\n\t 0 = Unknown\n\t 1 = Untrusted\n\t 2 = Marginal\n\t 3 = Full' +
                                     '\n\t 4 = Ultimate\033[0m\nTrust: ').format(k, kinfo[k]['name'], kinfo[k]['email']))
                    for dictk, dictv in trustmap.items():
                        if trust_in.lower().strip() == dictv[0]:
                            trust_lvl = int(dictk)
                        elif trust_in == str(dictk):
                            trust_lvl = int(dictk)
                    if not trust_lvl:
                        print('Not a valid trust level; skipping. Run kant again to fix.')
                        continue
                    kinfo[k]['trust'] = trustmap[trust_lvl][1]
                if 'local' not in kinfo[k].keys():
                    local = False
                    if args['keyservers']:
                        local_in = input('\nShould we push {0} to the keyserver(s) (\033[1mYES\033[0m/No)? '.format(k))
                        if local_in.lower().startswith('n'):
                            local = True
                    kinfo[k]['local'] = local
            return(kinfo)
        os.environ['GNUPGHOME'] = args['gpgdir']
        gpg = gpgme.Context()
        # Build out some info about keys
        kinfo = {}
        for k in self.keyids:
            if k not in kinfo.keys():
                kinfo[k] = {}
            else:
                continue  # The key was already parsed; don't waste time adding the info
            try:
                kobj = gpg.get_key(k)
                kinfo[k]['name'] = kobj.uids[0].name
                kinfo[k]['email'] = kobj.uids[0].email
            except gpgme.GpgmeError:
                print('Can\'t get information about key {0}; skipping.'.format(k))
                del(kinfo[k])
        if not args['batch']:
            if not args['trustlevel']:
                self.trusts = promptTrust(kinfo)
            else:
                for k in list(kinfo):
                    local = False
                    if 'trust' not in kinfo[k].keys():
                        for dictk, dictv in trustmap.items():
                            if args['trustlevel'].lower().strip() == dictv[0]:
                                trust_lvl = int(dictk)
                            elif args['trustlevel'] == str(dictk):
                                trust_lvl = int(dictk)
                        if not trust_lvl:
                            print('Not a valid trust level; skipping. Run kant again to fix.')
                            continue
                    if 'local' not in kinfo[k].keys():
                        if args['local']:
                            local = True
                    kinfo[k]['local'] = local
                    kinfo[k]['trust'] = trustmap[trust_lvl][1]
                self.trusts = kinfo
        else:
            self.trusts = {}
            csvd = {}  # We import the CSV into a totally separate dict so we can do some validation loops
            with open(self.args['keys'], 'r') as f:
                for row in csv.reader(f, delimiter = ',', quotechar = '"'):
                    csvd[row[0]] = {'trust': row[1].strip(),
                                    'local': row[2].strip(),
                                    'check': row[3].strip(),
                                    'notify': row[4].strip()}
            for k in list(csvd):
                if re.match('^<?[\w\.\+\-]+\@[\w-]+\.[a-z]{2,3}>?$', k):  # is it an email address?
                    fullkey = gpg.get_key(k)
                    csvd[fullkey.subkeys[0].fpr] = csvd[k]
                    del(csvd[k])
                    k = fullkey.subkeys[0].fpr
                if k not in trusts.keys():
                    self.trusts[k] = {}
                if 'trust' not in trusts[k].keys():
                    # Properly index the trust
                    strval = str(csvd[k]['trust']).lower().strip()
                    if strval == 'true':
                        self.trusts[k]['trust'] = True
                    elif strval == 'false':
                        self.trusts[k]['trust'] = False
                    elif strval == 'none':
                        self.trusts[k]['trust'] = None
                    else:
                        for dictk, dictv in trustmap.items():
                            if strval == dictv[0]:
                                self.trusts[k]['trust'] = trustmap[dictk][1]
                            elif strval == str(dictk):
                                self.trusts[k]['trust'] = trustmap[dictk][1]
                if 'trust' not in self.trusts[k].keys():  # yes, again. we make sure it was set. otherwise, we need to skip this key.
                    print('Key {0}: trust level "{1}" is invalid; skipping.'.format(k, csvd[k]['trust']))
                    del(self.trusts[k])
                    continue
                # Now we need to index whether we push or not.
                if 'local' not in self.trusts[k].keys():
                    strval = str(csvd[k]['local']).lower().strip()
                    if strval == 'true':
                        self.trusts[k]['local'] = True
                    elif strval == 'false':
                        self.trusts[k]['local'] = False
                    else:
                        for dictk, dictv in locmap.items():
                            if strval in dictv[0]:
                                self.trusts[k]['local'] = locmap[dictk][1]
                            elif strval == str(dictk):
                                self.trusts[k]['local'] = locmap[dictk][1]
                if 'local' not in self.trusts[k].keys():  # yep. double-check
                    print('Key {0}: local option "{1}" is invalid; skipping.'.format(k, csvd[k]['local']))
                    del(self.trusts[k])
                    continue
        # WHEW. THAT'S A LOT OF VALIDATIONS. Now the Business-End(TM)
        # Reverse mapping of constants to human-readable
        rmap = {gpgme.VALIDITY_NEVER: 'Never',
                gpgme.VALIDITY_UNKNOWN: 'Unknown',
                gpgme.VALIDITY_UNDEFINED: 'Untrusted',
                gpgme.VALIDITY_MARGINAL: 'Marginal',
                gpgme.VALIDITY_FULL: 'Full',
                gpgme.VALIDITY_ULTIMATE: 'Ultimate'}
        mykey = gpg.get_key(args['sigkey'])
        for k in list(self.trusts):
            keystat = None
            try:
                tkey = gpg.get_key(k)
            except gpgme.GpgmeError:
                print('Cannot find {0} in keyring at all; skipping.'.format(k))
                del(self.trusts[k])
                continue
            curtrust = rmap[tkey.owner_trust]
            newtrust = rmap[self.trusts[k]['trust']]
            if tkey.owner_trust == trusts[k]['trust']:
                self.trusts[k]['change'] = False
                continue  # Don't bother; we aren't changing the trust level, it's the same (OR we haven't trusted yet)
            elif tkey.owner_trust == gpgme.VALIDITY_UNKNOWN:
                keystat = 'a NEW TRUST'
            elif tkey.owner_trust > trusts[k]['trust']:
                keystat = 'a DOWNGRADE'
            elif tkey.owner_trust < trusts[k]['trust']:
                keystat = 'an UPGRADE'
            print(('\nKey {0} [{1} ({2})]:\n' +
                  '\tThis trust level ({3}) is {4} from the current trust level ({5}).').format(k,
                                                                                                kinfo[k]['name'],
                                                                                                kinfo[k]['email'],
                                                                                                newtrust,
                                                                                                keystat,
                                                                                                curtrust))
            tchk = input('Continue? (yes/\033[1mNO\033[0m) ')
            if tchk.lower().startswith('y'):
                self.trusts[k]['change'] = True
            else:
                self.trusts[k]['change'] = False
        for k in list(self.trusts):
            if self.trusts[k]['change']:
                print(k)
                gpg.editutil.edit_trust(ctx, ctx.get_key(k), self.trusts[k]['trust'])
        print()
        return(self.trusts)

    def sigKeys(self):  # The More Business-End(TM)
        os.environ['GNUPGHOME'] = args['gpgdir']
        ctx = gpg.Context()
        ctx.keylist_mode = gpg.KEYLIST_MODE_SIGS
        mkey = ctx.get_key(args['sigkey'])
        ctx.signers = [mkey]
        global_policy = {}
        for k in list(self.trusts):
            sign = True
            key = ctx.get_key(k)
            for uid in key.uids:
                for s in uid.signatures:
                    try:
                        signerkey = ctx.get_key(s.keyid).subkeys[0].fpr
                        if signerkey == mkey.subkeys[0].fpr:
                            sign = False  # We already signed this key
                    except gpgme.GpgError:
                        pass  # usually if we get this it means we don't have a signer's key in our keyring
            self.trusts[k]['sign'] = sign
        import pprint
        pprint.pprint(self.trusts)
            # edit_sign(ctx, key, index=0, local=False, norevoke=False, expire=True, check=0)
            #       index:    the index of the user ID to sign, starting at 1.  Sign all
            #       user IDs if set to 0.
            #       local:    make a local signature
            #       norevoke: make a non-revokable signature
            #       command:  the type of signature.  One of sign, lsign, tsign or nrsign.
            #       expire:   whether the signature should expire with the key.
            #       check:    Amount of checking performed.  One of:
            #         0 - no answer
            #         1 - no checking
            #         2 - casual checking
            #         3 - careful checking

            #gpgme.editutil.edit_sign(gpg, k, index = 0, lo


    def pushKeys():  # The Last Business-End(TM)
        pass

    def modifyDirmngr(self, op):
        if not self.args['keyservers']:
            return()
        pid = str(os.getpid())
        activecfg = os.path.join(self.args['gpgdir'], 'dirmngr.conf')
        bakcfg = '{0}.{1}'.format(activecfg, pid)
        if op in ('new', 'start'):
            if os.path.lexists(activecfg):
                shutil.copy2(activecfg, bakcfg)
            with open(bakcfg, 'r') as read, open(activecfg, 'w') as write:
                for line in read:
                    if not line.startswith('keyserver '):
                        write.write(line)
            with open(activecfg, 'a') as f:
                for s in self.args['keyservers']:
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
        ctx = gpg.Context()
        for k in ctx.keylist(None, True):  # params are query and secret keyring, respectively
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
                      metavar = 'KEYS | /path/to/batchfile',
                      required = True,
                      help = 'A single/comma-separated list of keys to sign, ' +
                             'trust, & notify. Can also be an email address. ' +
                             'If -b/--batch is specified, this should instead be ' +
                             'a path to the batch file. See the man page for more info.')
    args.add_argument('-K',
                      '--sigkey',
                      dest = 'sigkey',
                      default = defkey,
                      help = 'The key to use when signing other keys. Default is \033[1m{0}\033[0m.'.format(defkey))
    args.add_argument('-t',
                      '--trust',
                      dest = 'trustlevel',
                      default = None,
                      help = 'The trust level to automatically apply to all keys ' +
                             '(if not specified, kant will prompt for each key). ' +
                             'See BATCHFILE/TRUSTLEVEL in the man page for trust ' +
                             'level notations.')
    args.add_argument('-c',
                      '--check',
                      dest = 'checklevel',
                      default = None,
                      help = 'The level of checking done (if not specified, kant will ' +
                             'prompt for each key). See -b/--batch for check level notations.')
    args.add_argument('-l',
                      '--local',
                      dest = 'local',
                      default = 'false',
                      help = 'Make the signature(s) local-only (i.e. don\'t push to a keyserver).')
    args.add_argument('-n',
                      '--no-notify',
                      dest = 'notify',
                      action = 'store_false',
                      help = 'If specified, do NOT notify any key recipients that you\'ve signed ' +
                             'their key, even if KANT is able to.')
    args.add_argument('-s',
                      '--keyservers',
                      dest = 'keyservers',
                      default = defkeyservers,
                      help = 'The comma-separated keyserver(s) to push to.\n' +
                             'Default keyserver list is: \n\n\t\033[1m{0}\033[0m\n\n'.format(re.sub(',',
                                                                                                    '\n\t',
                                                                                                    defkeyservers)))
    args.add_argument('-b',
                      '--batch',
                      dest = 'batch',
                      action = 'store_true',
                      help = 'If specified, -k/--keys is a CSV file to use as a ' +
                             'batch run. See the BATCHFILE section in the man page for more info.')
    args.add_argument('-D',
                      '--gpgdir',
                      dest = 'gpgdir',
                      default = defgpgdir,
                      help = 'The GnuPG configuration directory to use (containing\n' +
                             'your keys, etc.); default is \033[1m{0}\033[0m.'.format(defgpgdir))
    args.add_argument('-T',
                      '--testkeyservers',
                      dest = 'testkeyservers',
                      action = 'store_true',
                      help = 'If specified, initiate a test connection with each\n'
                             'set keyserver before anything else. Disabled by default.')
    return(args)

def verifyArgs(args):
    ## Some pythonization...
    if not args['batch']:
        args['keys'] = [re.sub('\s', '', k) for k in args['keys'].split(',')]
    else:
        ## Batch file
        batchfilepath = os.path.abspath(os.path.expanduser(args['keys']))
        if not os.path.isfile(batchfilepath):
            raise ValueError('{0} does not exist or is not a regular file.'.format(batchfilepath))
        else:
            args['keys'] = batchfilepath
    args['keyservers'] = [re.sub('\s', '', s) for s in args['keyservers'].split(',')]
    args['keyservers'] = [serverParser(s) for s in args['keyservers']]
    ## Key(s) to sign
    args['rcpts'] = {}
    if not args['batch']:
        keyiter = args['keys']
    else:
        keyiter = []
        with open(args['keys'], 'r') as f:
            for row in csv.reader(f, delimiter = ',', quotechar = '"'):
                keyiter.append(row[0])
    for k in keyiter:
        args['rcpts'][k] = {}
        try:
            int(k, 16)
            ktype = 'fpr'
        except:  # If it isn't a valid key ID...
            if not re.match('^<?[\w\.\+\-]+\@[\w-]+\.[a-z]{2,3}>?$', k):  # is it an email address?
                raise ValueError('{0} is not a valid email address'.format(k))
            else:
                ktype = 'email'
        args['rcpts'][k]['type'] = ktype
        if ktype == 'fpr' and not len(k) == 40:  # Security is important. We don't want users getting collisions, so we don't allow shortened key IDs.
            raise ValueError('{0} is not a full 40-char key ID or key fingerprint'.format(k))
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
            ctx = gpg.Context()
        except:
            raise RuntimeError('Could not use {0} as a GnuPG home'.format(args['gpgdir']))
        # Now we need to verify that the private key exists...
        try:
            sigkey = ctx.get_key(args['sigkey'], True)
        except GpgmeError:
            raise ValueError('Cannot use key {0}'.format(args['sigkey']))
        # And that it is an eligible candidate to use to sign.
        if not sigkey.can_sign or True in (sigkey.revoked, sigkey.expired, sigkey.disabled):
            raise ValueError('{0} is not a valid candidate for signing'.format(args['sigkey']))
    ## Keyservers
    if args['testkeyservers']:
        for s in args['keyservers']:
            # Test to make sure the keyserver is accessible.
            v6test = socket(AF_INET6, SOCK_DGRAM)
            try:
                v6test.connect(('ipv6.square-r00t.net', 0))
                nettype = AF_INET6  # We have IPv6 intarwebz
            except:
                nettype = AF_INET  # No IPv6, default to IPv4
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
                    raise OSError('Keyserver {0} is not available'.format(uristr))
                else:
                    print('Keyserver {0} is accepting connections.'.format(uristr))
                sock.close()
    return(args)

def main():
    rawargs = parseArgs()
    args = verifyArgs(vars(rawargs.parse_args()))
    sess = sigsession(args)
    sess.modifyDirmngr('new')
    sess.getKeys()
    sess.trustKeys()
    sess.sigKeys()
    sess.modifyDirmngr('old')

if __name__ == '__main__':
    main()
