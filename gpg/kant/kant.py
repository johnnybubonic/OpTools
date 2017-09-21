#!/usr/bin/env python3

import argparse
import base64
import csv
import datetime
import json
import lzma
import operator
import os
import re
import shutil
import smtplib
import subprocess
from email.message import Message
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import reduce
from io import BytesIO
from socket import *
import urllib.parse
import jinja2 # non-stdlib; Arch package is python-jinja2
import gpg              # non-stdlib; Arch package is "python-gpgme" - see:
import gpg.constants    #   https://git.archlinux.org/svntogit/packages.git/tree/trunk/PKGBUILD?h=packages/gpgme and
import gpg.errors       #   https://gnupg.org/ftp/gcrypt/gpgme/  (incl. python bindings in build)
import pprint  # development debug


class SigSession(object):  # see docs/REFS.funcs.struct.txt
    def __init__(self, args):
        # These are the "stock" templates for emails. It's a PITA, but to save some space since we store them
        # inline in here, they're XZ'd and base64'd.
        self.email_tpl = {}
        self.email_tpl['plain'] = ('/Td6WFoAAATm1rRGAgAhARwAAAAQz1jM4ATxAnZdACQZSZhvFgKNdKNXbSf05z0ZPvTvmdQ0mJQg' +
                                    'atgzhPVeLKxz22bhxedC813X5I8Gn2g9q9Do2jPPgXOzysImWXoraY4mhz0BAo2Zx1u6AiQQLdN9' +
                                    '/jwrDrUEtb8M/QzmRd+8JrYN8s8vhViJZARMNHYnPeQK5GYEoGZEQ8l2ULmpTjAn9edSnrMmNSb2' +
                                    'EC86CuyhaWDPsQeIamWW1t+MWmgsggE3xKYADKXHMQyXvhv/TAn987dEbzmrkpg8PCjxWt1wKRAr' +
                                    'siDpCGvXLiBwnDtN1D7ocwbZVKty2GELbYt0f0CT7n5Pyu9n0P7QMnErM38kLR1nReopQp41+CsG' +
                                    'orb8EpGGVdFa7sSWSANQtGTjx/1JHecpkTN8xX4kAjMWKYujWlZi/HzN7y/W5GDJM3ycVEUTsDRV' +
                                    '6AusncRBFbo4/+K6cn5WCrhqd5jY2vDJR6KcO0O3usHUMzvOF0S0CZhUbA3Mil5DmPwFrdFrESby' +
                                    'O1xH3uvgHpA5X91qkpEajokOOkY3FZm0oeANh9AMoMfDFTuqi41Nq9Myk4VKNEfzioChn9IfFxX0' +
                                    'Luw6OyXtWJdpe3BvO7pWazLhvdIY4poh9brvJ25cG1kDMOlmC3NEb+POeqQ5aUr4XaRqFstk3grb' +
                                    '8EjiGBzg18uHsbhjyReXnZprJjwzWUdwpV6j+2JFI13UEp16oTyTwyhHdpAmAg+lQJQxtcMpnUeX' +
                                    '/xBkQGs+rqe0e/i8ZQ80XsLAoScxUL+45v9vANYV+lCWRnm/2GZOtCFs1Cb4t9hOeV0P1cwxw7fG' +
                                    'b1A921JUkHbASFiv2EFsgf0lkvnMgz2slNXKcLuwB6X0CAAAALypR4JWDUR6AAGSBfIJAABGCaV4' +
                                    'scRn+wIAAAAABFla')
        self.email_tpl['html'] = ('/Td6WFoAAATm1rRGAgAhARwAAAAQz1jM4AXfAtVdAB4aCobvStaHNqdVBn1LjZcL+G+98rmZ7eGZ' +
                                    'Wqx+3LjENIv37L1aGPICZDRBrsBugzVSasRBHkdHMrWW7SsPfRzw6btQfASTHLr48auPJlJgXTnb' +
                                    'vgDd2ELrs6p5m5Wip3qD4NeNuwj4QMcxszWF1vLa1oZiNAmCSunIF8bNTw+lmI50h2M6bXfx80Og' +
                                    'T2HGcuTp07Mp+XLyZQJ5lbQyu5BRhwyKpu14sq9qrVkxmYt8AAxgUyhvRkooHSuug4O8ArMFXqqX' +
                                    'usX9P3zERAsi/TqWIFaG0xoBdrWf/zpGtsVQ+5TtCGOfUHGfIBaNy9Q+FOvfLJFYEzxac992Fkd0' +
                                    'as4RsN31FaySbBmZ8eB3zGbpjS7QH7CA70QYkRcYXcjWE9xHD3Wzxa3DFE0ihKAyVwakxvjgYa2B' +
                                    '7G6uYO606c+a6vHfPhgvY7Eph+I7ip0btfBbcKZ+XBSd0DtCd7ZvI7vlGJdW2/OBXHfNmCndMP1W' +
                                    'Ujd0ASQAQBbJr4rIxYygckSPWti4nBe9JpKTVWqdWRXWjeYGci1dKIjKs7JfS1PGJR50iuyANBun' +
                                    'yQ9oIRafb3nreBqtpXZ4LKM5hC697BaeOIcocXyMALf0a06AUmIaRQfO3AZrPxyOPH3EYOKIMrjM' +
                                    'EosihPVVyYuKUVOg3wWq5aeIC9zM7Htw4FNh2NB5QDYY6HxIqIVUfHCGz+4GaPBVaf0eie8kHaQR' +
                                    'xj+DkAiWQDmN/JRZeTlsy4d3P8XcArOLmxzql/iDzFqtzpD5d91o8I3HU9BJlDJFPs8bC2eCjYs8' +
                                    'o3WJET/UIch6YXQOemXa72aWdBVSytfKBMtL7uekd4ARGbFZYyW2x1agkAZGiWt7gwY8RVEoKyZH' +
                                    'bbvIvOhQ/j1BDuJFJO3BEgekeLhBPpG7cEewseXjGjoWZWtGr+qFTI//w+oDtdqGtJaGtELL3WYU' +
                                    '/tMiQU9AfXkTsODAjvduAAAAAIixVQ23iBDFAAHxBeALAADIP1EPscRn+wIAAAAABFla')
        # Set up a dict of some constants and mappings
        self.maps = {}
        # Keylist modes
        self.maps['keylist'] = {'local': gpg.constants.KEYLIST_MODE_LOCAL,  # local keyring
                                'remote': gpg.constants.KEYLIST_MODE_EXTERN,  # keyserver
                                # both - this is SUPPOSED to work, but doesn't seem to... it's unreliable at best?
                                'both': gpg.constants.KEYLIST_MODE_LOCAL|gpg.constants.KEYLIST_MODE_EXTERN}
        # Validity/trust levels
        self.maps['trust'] = {-1: ['never', gpg.constants.VALIDITY_NEVER], # this is... probably? not ideal, but. Never trust the key.
                               0: ['unknown', gpg.constants.VALIDITY_UNKNOWN],  # The key's trust is unknown - typically because it hasn't been set yet.
                               1: ['untrusted', gpg.constants.VALIDITY_UNDEFINED],  # The key is explicitly set to a blank trust
                               2: ['marginal', gpg.constants.VALIDITY_MARGINAL],  # Trust a little.
                               3: ['full', gpg.constants.VALIDITY_FULL],  # This is going to be the default for verified key ownership.
                               4: ['ultimate', gpg.constants.VALIDITY_ULTIMATE]}  # This should probably only be reserved for keys you directly control.
        # Validity/trust reverse mappings - see self.maps['trust'] for the meanings of these
        # Used for fetching display/feedback
        self.maps['rtrust'] = {gpg.constants.VALIDITY_NEVER: 'Never',
                               gpg.constants.VALIDITY_UNKNOWN: 'Unknown',
                               gpg.constants.VALIDITY_UNDEFINED: 'Untrusted',
                               gpg.constants.VALIDITY_MARGINAL: 'Marginal',
                               gpg.constants.VALIDITY_FULL: 'Full',
                               gpg.constants.VALIDITY_ULTIMATE: 'Ultimate'}
        # Local signature and other binary (True/False) mappings
        self.maps['binmap'] = {0: ['no', False],
                               1: ['yes', True]}
        # Level of care taken when checking key ownership/valid identity
        self.maps['check'] = {0: ['unknown', 0],
                              1: ['none', 1],
                              2: ['casual', 2],
                              3: ['careful', 3]}
        # Default protocol/port mappings for keyservers
        self.maps['proto'] = {'hkp': [11371, ['tcp', 'udp']],  # Standard HKP protocol
                              'hkps': [443, ['tcp']],  # Yes, same as https
                              'http': [80, ['tcp']],  # HTTP (plaintext)
                              'https': [443, ['tcp']],  # SSL/TLS
                              'ldap': [389, ['tcp', 'udp']],  # Includes TLS negotiation since it runs on the same port
                              'ldaps': [636, ['tcp', 'udp']]}  # SSL
        self.maps['hashalgos'] = {gpg.constants.MD_MD5: 'md5',
                                  gpg.constants.MD_SHA1: 'sha1',
                                  gpg.constants.MD_RMD160: 'ripemd160',
                                  gpg.constants.MD_MD2: 'md2',
                                  gpg.constants.MD_TIGER: 'tiger192',
                                  gpg.constants.MD_HAVAL: 'haval',
                                  gpg.constants.MD_SHA256: 'sha256',
                                  gpg.constants.MD_SHA384: 'sha384',
                                  gpg.constants.MD_SHA512: 'sha512',
                                  gpg.constants.MD_SHA224: 'sha224',
                                  gpg.constants.MD_MD4: 'md4',
                                  gpg.constants.MD_CRC32: 'crc32',
                                  gpg.constants.MD_CRC32_RFC1510: 'crc32rfc1510',
                                  gpg.constants.MD_CRC24_RFC2440: 'crc24rfc2440'}
        # Now that all the static data's set up, we can continue.
        self.args = self.verifyArgs(args)  # Make the args accessible to all functions in the class - see docs/REF.args.struct.txt
        # Get the GPGME context
        try:
            os.environ['GNUPGHOME'] = self.args['gpgdir']
            self.ctx = gpg.Context()
        except:
            raise RuntimeError('Could not use {0} as a GnuPG home'.format(self.args['gpgdir']))
        self.cfgdir = os.path.join(os.environ['HOME'], '.kant')
        if not os.path.isdir(self.cfgdir):
            print('No KANT configuration directory found; creating one at {0}...'.format(self.cfgdir))
        os.makedirs(self.cfgdir, exist_ok = True)
        self.keys = {}   # See docs/REF.keys.struct.txt
        self.mykey = {}  # ""
        self.tpls = {}   # Email templates will go here
        self.getTpls()   # Build out self.tpls
        return(None)

    def getEditPrompt(self, key, cmd):  # "key" should be the FPR of the primary key
        # This mapping defines the default "answers" to the gpgme key editing.
        # https://www.apt-browse.org/browse/debian/wheezy/main/amd64/python-pyme/1:0.8.1-2/file/usr/share/doc/python-pyme/examples/t-edit.py
        # https://searchcode.com/codesearch/view/20535820/
        # https://git.gnupg.org/cgi-bin/gitweb.cgi?p=gnupg.git;a=blob;f=doc/DETAILS
        # You can get the prompt identifiers and status indicators without grokking the source
        # by first interactively performing the type of edit(s) you want to do with this command:
        # gpg --status-fd 2 --command-fd 2 --edit-key <KEY_ID>
        if key['trust'] >= gpg.constants.VALIDITY_FULL:  # For tsigning, it only prompts for two trust levels:
            _loctrust = 2  # "I trust fully"
        else:
            _loctrust = 1  # "I trust marginally"
        # TODO: make the trust depth configurable. 1 is probably the safest, but we try to guess here.
        # "Full" trust is a pretty big thing.
        if key['trust'] >= gpg.constants.VALIDITY_FULL:
            _locdepth = 2  # Allow +1 level of trust extension
        else:
            _locdepth = 1  # Only trust this key
        _map = {'cmds': ['trust', 'fpr', 'sign', 'tsign', 'lsign', 'nrsign', 'grip', 'list',  # Valid commands
                         'uid', 'key', 'check', 'deluid', 'delkey', 'delsig', 'pref', 'showpref',
                         'revsig', 'enable', 'disable', 'showphoto', 'clean', 'minimize', 'save',
                         'quit'],
                'prompts': {'edit_ownertrust': {'value': str(key['trust']),  # Pulled at time of call
                                                'set_ultimate': {'okay': 'yes'}},  # If confirming ultimate trust, we auto-answer yes
                            'untrusted_key': {'override': 'yes'},  # We don't care if it's untrusted
                            'pklist': {'user_id': {'enter': key['pkey']['email']}},  # Prompt for a user ID - can we change this to key ID?
                            'sign_uid': {'class': str(key['check']),  # The certification/"check" level
                                         'okay': 'yes'},  # Are you sure that you want to sign this key with your key..."
                            'trustsig_prompt': {'trust_value': str(_loctrust),  # This requires some processing; see above
                                                'trust_depth': str(_locdepth),  # The "depth" of the trust signature.
                                                'trust_regexp': None},  # We can "Restrict" trust to certain domains, but this isn't really necessary.
                            'keyedit': {'prompt': cmd,  # Initiate trust editing
                                        'save': {'okay': 'yes'}}}}  # Save if prompted
        return(_map)
    
    def getTpls(self):
        for t in ('plain', 'html'):
            _tpl_file = os.path.join(self.cfgdir, 'email.{0}.j2'.format(t))
            if os.path.isfile(_tpl_file):
                with open(_tpl_file, 'r') as f:
                    self.tpls[t] = f.read()
            else:
                self.tpls[t] = lzma.decompress(base64.b64decode(email_tpl[t]),
                                               format = lzma.FORMAT_XZ,
                                               memlimit = None,
                                               filters = None).decode('utf-8')
                with open(_tpl_file, 'w') as f:
                    f.write('{0}'.format(self.tpls[t]))
                print('Created: {0}'.format(tpl_file))
        return(self.tpls)

    def modifyDirmngr(self, op):
        if not self.args['keyservers']:
            return()
        _pid = str(os.getpid())
        _activecfg = os.path.join(self.args['gpgdir'], 'dirmngr.conf')
        _activegpgconf = os.path.join(self.args['gpgdir'], 'gpg.conf')
        _bakcfg = '{0}.{1}'.format(_activecfg, _pid)
        _bakgpgconf = '{0}.{1}'.format(_activegpgconf, _pid)
        ## Modify files
        if op in ('new', 'start', 'replace'):
            # Replace the keyservers
            if os.path.lexists(_activecfg):
                shutil.copy2(_activecfg, _bakcfg)
            with open(_bakcfg, 'r') as read, open(_activecfg, 'w') as write:
                for line in read:
                    if not line.startswith('keyserver '):
                        write.write(line)
            with open(_activecfg, 'a') as f:
                for s in self.args['keyservers']:
                    _uri = '{0}://{1}:{2}'.format(s['proto'],
                                                  s['server'],
                                                  s['port'][0])
                    f.write('keyserver {0}\n'.format(_uri))
            # Use stronger ciphers, etc. and prompt for check/certification levels
            if os.path.lexists(_activegpgconf):
                shutil.copy2(_activegpgconf, _bakgpgconf)
            with open(_activegpgconf, 'w') as f:
                f.write('cipher-algo AES256\ndigest-algo SHA512\ncert-digest-algo SHA512\ncompress-algo BZIP2\nask-cert-level\n')
        ## Restore files
        if op in ('old', 'stop', 'restore'):
            # Restore the keyservers
            if os.path.lexists(_bakcfg):
                with open(_bakcfg, 'r') as read, open(_activecfg, 'w') as write:
                    for line in read:
                        write.write(line)
                os.remove(_bakcfg)
            else:
                os.remove(_activecfg)
            # Restore GPG settings
            if os.path.lexists(_bakgpgconf):
                with open(_bakgpgconf, 'r') as read, open(_activegpgconf, 'w') as write:
                    for line in read:
                        write.write(line)
                os.remove(_bakgpgconf)
            else:
                os.remove(_activegpgconf)
        subprocess.run(['gpgconf', '--reload', 'dirmngr'])  # I *really* wish we could do this via GPGME.
        return()

    def getKeys(self):
        _keyids = []
        _keys = {}
        # Do we have the key already? If not, fetch.
        for r in list(self.args['rcpts'].keys()):
            if self.args['rcpts'][r]['type'] == 'fpr':
                _keyids.append(r)
                self.ctx.set_keylist_mode(self.maps['keylist']['remote'])
                try:
                    _k = self.ctx.get_key(r)
                except:
                    print('{0}: We could not find this key on the keyserver.'.format(r))  # Key not on server
                    del(self.args['rcpts'][r])
                    _keyids.remove(r)
                    continue
                self.ctx.set_keylist_mode(self.maps['keylist']['local'])
                _keys[r] = {'fpr': r,
                            'obj': _k,
                            'created': _k.subkeys[0].timestamp}
                if 'T' in str(_keys[r]['created']):
                    _keys[r]['created'] = int(datetime.datetime.strptime(_keys[r]['created'],
                                                                         '%Y%m%dT%H%M%S').timestamp())
            if self.args['rcpts'][r]['type'] == 'email':
                # We need to actually do a lookup on the email address.
                _keytmp = []
                for k in self.ctx.keylist(r, mode = self.maps['keylist']['remote']):
                    _keytmp.append(k)
                for k in _keytmp:
                    _keys[k.fpr] = {'fpr': k.fpr,
                                    'obj': k,
                                    'created': k.subkeys[0].timestamp,
                                    'uids': {}}
                    # Per the docs (<gpg>/docs/DETAILS, "*** Field 6 - Creation date"),
                    # they may change this to ISO 8601...
                    if 'T' in str(_keys[k.fpr]['created']):
                        _keys[k.fpr]['created'] = int(datetime.datetime.strptime(_keys[k.fpr]['created'],
                                                                                 '%Y%m%dT%H%M%S').timestamp())
                    for s in k.uids:
                        _keys[k.fpr]['uids'][s.email] = {'comment': s.comment,
                                                         'updated': s.last_update}
                if len(_keytmp) > 1:  # Print the keys and prompt for a selection.
                    
                    print('\nWe found the following keys for {0}...\n\nKEY ID:'.format(r))
                    for s in _keytmp:
                        print('{0}\n{1:6}(Generated at {2})  UIDs:'.format(s.fpr,
                                                                           '',
                                                                           datetime.datetime.utcfromtimestamp(s.subkeys[0].timestamp)))
                        for u in s.uids:
                            if u.last_update == 0:
                                _updated = 'Never/Unknown'
                            else:
                                _updated = datetime.datetime.utcfromtimestamp(u.last_update)
                            print('{0:42}(Updated {3}) <{2}> {1}'.format('',
                                                                         u.comment,
                                                                         u.email,
                                                                         _updated))
                        print()
                    while True:
                        key = input('Please enter the (full) appropriate key: ')
                        if key not in _keys.keys():
                            print('Please enter a full key ID from the list above or hit ctrl-d to exit.')
                        else:
                            _keyids.append(key)
                            break
                else:
                    if len(_keytmp) == 0:
                        print('Could not find {0}!'.format(r))
                        del(self.args['rcpts'][r])
                        continue
                    _keyids.append(k.fpr)
                    print('\nFound key {0} for {1} (Generated at {2}):'.format(_keys[k.fpr]['fpr'],
                                                                               r,
                                                                               datetime.datetime.utcfromtimestamp(_keys[k.fpr]['created'])))
                    for email in _keys[k.fpr]['uids']:
                        if _keys[k.fpr]['uids'][email]['updated'] == 0:
                            _updated = 'Never/Unknown'
                        else:
                            _updated = datetime.datetime.utcfromtimestamp(_keys[k.fpr]['uids'][email]['updated'])
                        print('\t(Generated {2}) {0} <{1}>'.format(_keys[k.fpr]['uids'][email]['comment'],
                                                                   email,
                                                                   _updated))
                    print()
        ## And now we can (FINALLY) fetch the key(s).
        print(_keyids)
        for g in _keyids:
            try:
                self.ctx.op_import_keys([_keys[g]['obj']])
            except gpg.errors.GPGMEError:
                print('Key {0} could not be found on the keyserver'.format(g))  # The key isn't on the keyserver
        self.ctx.set_keylist_mode(self.maps['keylist']['local'])
        for k in _keys:
            if k not in _keyids:
                continue
            _key = _keys[k]['obj']
            self.keys[k] = {'pkey': {'email': _key.uids[0].email,
                                     'name': _key.uids[0].name,
                                     'creation': datetime.datetime.utcfromtimestamp(_keys[k]['created']),
                                     'key': _key},
                            'trust': self.args['trustlevel'],  # Not set yet; we'll modify this later in buildKeys().
                            'local': self.args['local'],  # Not set yet; we'll modify this later in buildKeys().
                            'notify': self.args['notify'],  # Same...
                            'sign': True,  # We don't need to prompt for this since we detect if we need to sign or not
                            'change': None,  # ""
                            'status': None}  # Same.
            # And we add the subkeys in yet another loop.
            self.keys[k]['subkeys'] = {}
            self.keys[k]['uids'] = {}
            for s in _key.subkeys:
                self.keys[k]['subkeys'][s.fpr] = datetime.datetime.utcfromtimestamp(s.timestamp)
            for u in _key.uids:
                self.keys[k]['uids'][u.email] = {'name': u.name,
                                                 'comment': u.comment,
                                                 'updated': datetime.datetime.utcfromtimestamp(u.last_update)}
        del(_keys)
        return()

    def buildKeys(self):
        self.getKeys()
        # Before anything else, let's set up our own key info.
        _key = self.ctx.get_key(self.args['sigkey'], secret = True)
        self.mykey = {'pkey': {'email': _key.uids[0].email,
                               'name': _key.uids[0].name,
                               'creation': datetime.datetime.utcfromtimestamp(_key.subkeys[0].timestamp),
                               'key': _key},
                      'trust': 'ultimate',  # No duh. This is our own key.
                      'local': False,  # We keep our own key array separate, so we don't push it anyways.
                      'notify': False,  # ""
                      'check': None,  # ""
                      'change': False,  # ""
                      'status': None,  # ""
                      'sign': False}  # ""
        self.mykey['subkeys'] = {}
        self.mykey['uids'] = {}
        for s in _key.subkeys:
            self.mykey['subkeys'][s.fpr] = datetime.datetime.utcfromtimestamp(s.timestamp)
        for u in _key.uids:
            self.mykey['uids'][u.email] = {'name': u.name,
                                           'comment': u.comment,
                                           'updated': datetime.datetime.utcfromtimestamp(u.last_update)}
        # Now let's set up our trusts.
        if self.args['batch']:
            self.batchParse()
        else:
            for k in list(self.keys.keys()):
                self.promptTrust(k)
                self.promptCheck(k)
                self.promptLocal(k)
                self.promptNotify(k)
        # In case we removed any keys, we have to run this outside of the loops
        for k in list(self.keys.keys()):
            for t in ('trust', 'local', 'check', 'notify'):
                self.keysCleanup(k, t)
        # TODO: populate self.keys[key]['change']; we use this for trust (but not sigs)
        return()

    def batchParse(self):
        # First we grab the info from CSV
        csvlines = csv.reader(self.csvraw, delimiter = ',', quotechar = '"')
        for row in csvlines:
            row[0] = row[0].replace('<', '').replace('>', '')
            try:
                if self.args['rcpts'][row[0]]['type'] == 'fpr':
                    k = row[0]
                else:  # It's an email.
                    key_set = False
                    while not key_set:
                        for i in list(self.keys.keys()):
                            if row[0] in list(self.keys[i]['uids'].keys()):
                                k = i
                                key_set = True
                self.keys[k]['trust'] = row[1].lower().strip()
                self.keys[k]['local'] = row[2].lower().strip()
                self.keys[k]['check'] = row[3].lower().strip()
                self.keys[k]['notify'] = row[4].lower().strip()
            except KeyError:
                continue  # It was deemed to be an invalid key earlier
        return()

    def promptTrust(self, k):
        if 'trust' not in self.keys[k].keys() or not self.keys[k]['trust']:
            trust_in = input(('\nWhat trust level should we assign to {0}? (The default is '+
                              'Marginal.)\n\t\t\t\t     ({1} <{2}>)' +
                             '\n\n\t\033[1m-1 = Never\n\t 0 = Unknown\n\t 1 = Untrusted\n\t 2 = Marginal\n\t 3 = Full' +
                             '\n\t 4 = Ultimate\033[0m\nTrust: ').format(k,
                                                                         self.keys[k]['pkey']['name'],
                                                                         self.keys[k]['pkey']['email']))
            if trust_in == '':
                trust_in = 'marginal'  # Has to be a str, so we can "pretend" it was entered
            self.keys[k]['trust'] = trust_in
        return()

    def promptCheck(self, k):
        if 'check' not in self.keys[k].keys() or self.keys[k]['check'] == None:
            check_in = input(('\nHow carefully have you checked {0}\'s validity of identity/ownership of the key? ' +
                              '(Default is Unknown.)\n' +
                              '\n\t\033[1m0 = Unknown\n\t1 = None\n\t2 = Casual\n\t3 = Careful\033[0m\nCheck level: ').format(k))
            if check_in == '':
                check_in = 'unknown'
            self.keys[k]['check'] = check_in
        return()
    
    def promptLocal(self, k):
        if 'local' not in self.keys[k].keys() or self.keys[k]['local'] == None:
            if self.args['keyservers']:
                local_in = input(('\nShould we locally sign {0} '+
                                  '(if yes, the signature will be non-exportable; if no, we will be able to push to a keyserver) ' +
                                  '(Yes/\033[1mNO\033[0m)? ').format(k))
                if local_in == '':
                    local_in = False
                self.keys[k]['local'] = local_in
        return()

    def promptNotify(self, k):
        if 'notify' not in self.keys[k].keys() or self.keys[k]['notify'] == None:
            notify_in = input(('\nShould we notify {0} (via <{1}>) (\033[1mYES\033[0m/No)? ').format(k,
                                                                                                     self.keys[k]['pkey']['email']))
            if notify_in == '':
                notify_in = True
            self.keys[k]['local'] = local_in
        return()

    def keysCleanup(self, k, t):  # At some point, this WHOLE thing would probably be cleaner with bitwise flags...
        s = t
        _errs = {'trust': 'trust level',
                 'local': 'local signature option',
                 'check': 'check level',
                 'notify': 'notify flag'}
        if k not in self.keys.keys():
            return()  # It was deleted already.
        if t in ('local', 'notify'):  # these use a binary mapping
            t = 'binmap'
            # We can do some basic stuff right here.
            if str(self.keys[k][s]).lower() in ('n', 'no', 'false'):
                self.keys[k][s] = False
                return()
            elif str(self.keys[k][s]).lower() in ('y', 'yes', 'true'):
                self.keys[k][s] = True
                return()
        # Make sure we have a known value. These will ALWAYS be str's, either from the CLI or CSV.
        value_in = str(self.keys[k][s]).lower().strip()
        for dictk, dictv in self.maps[t].items():
            if value_in == dictv[0]:
                self.keys[k][s] = int(dictk)
            elif value_in == str(dictk):
                self.keys[k][s] = int(dictk)
        if not isinstance(self.keys[k][s], int):  # It didn't get set
            print('{0}: "{1}" is not a valid {2}; skipping. Run kant again to fix.'.format(k, self.keys[k][s], _errs[s]))
            del(self.keys[k])
            return()
        # Determine if we need to change the trust.
        if t == 'trust':
            cur_trust = self.keys[k]['pkey']['key'].owner_trust
            if cur_trust == self.keys[k]['trust']:
                self.keys[k]['change'] = False
            else:
                self.keys[k]['change'] = True
        return()
    
    def sigKeys(self):  # The More Business-End(TM)
        # NOTE: If the trust level is anything but 2 (the default), we should use op_interact() instead and do a tsign.
        self.ctx.keylist_mode = gpg.constants.KEYLIST_MODE_SIGS
        _mkey = self.mykey['pkey']['key']
        self.ctx.signers = [_mkey]
        for k in list(self.keys.keys()):
            key = self.keys[k]['pkey']['key']
            for uid in key.uids:
                for s in uid.signatures:
                    try:
                        signerkey = ctx.get_key(s.keyid).subkeys[0].fpr
                        if signerkey == mkey.subkeys[0].fpr:
                            self.trusts[k]['sign'] = False  # We already signed this key
                    except gpgme.GpgError:
                        pass  # usually if we get this it means we don't have a signer's key in our keyring
        # And again, we loop. ALLLLL that buildup for one line.
        for k in list(self.keys.keys()):
            # TODO: configure to allow for user-entered expiration?
            if self.keys[k]['sign']:
                self.ctx.key_sign(self.keys[k]['pkey']['key'], local = self.keys[k]['local'])
        return()

    class KeyEditor(object):
        def __init__(self, optmap):
            self.replied_once = False  # This is used to handle the first prompt vs. the last
            self.optmap = optmap
            return(None)

        def editKey(self, status, args, out):
            _result = None
            out.seek(0, 0)
            def mapDict(m, d):
                return(reduce(operator.getitem, m, d))
            if args == 'keyedit.prompt' and self.replied_once:
                _result = 'quit'
            elif status == 'KEY_CONSIDERED':
                _result = None
                self.replied_once = False
            elif status == 'GET_LINE':
                self.replied_once = True
                _ilist = args.split('.')
                _result = mapDict(_ilist, self.optmap['prompts'])
                if not _result:
                    _result = None
            return(_result)

    def trustKeys(self):  # The Son of Business-End(TM)
        # TODO: add check for change
        for k in list(self.keys.keys()):
            _key = self.keys[k]
            if _key['change']:
                _map = self.getEditPrompt(_key, 'trust')
                out = gpg.Data()
                self.ctx.interact(_key['pkey']['key'], self.KeyEditor(_map).editKey, sink = out, fnc_value = out)
                out.seek(0, 0)
        return()
    
    def pushKeys(self):  # The Last Business-End(TM)
        for k in list(self.keys.keys()):
            if not self.keys[k]['local'] and self.keys[k]['sign']:
                self.ctx.op_export(k, gpg.constants.EXPORT_MODE_EXTERN, None)
        return()

    class Mailer(object):  # I lied; The Return of the Business-End(TM)
        def __init__(self):
            _homeconf = os.path.join(os.environ['HOME'], '.msmtprc')
            _sysconf = '/etc/msmtprc'
            self.msmtp = {'conf': None}
            if not os.path.isfile(_homeconf):
                if not os.path.isfile(_sysconf):
                    self.msmtp['conf'] = False
                else:
                    self.msmtp['conf'] = _sysconf
            else:
                self.msmtp['conf'] = _homeconf
            if self.msmtp['conf']:
                # Okay. So we have a config file, which we're assuming to be set up correctly.
                # Now we need to parse the config.
                self.msmtp['cfg'] = self.getCfg()
            return(None)

        def getCfg(self):
            cfg = {'default': None, 'defaults': {}}
            _defaults = False
            _acct = None
            with open(self.msmtp['conf'], 'r') as f:
                _cfg_raw = f.read()
            for l in _cfg_raw.splitlines():
                if re.match('^\s?(#.*|)$', l):
                    continue  # Skip over blank and commented lines
                _line = [i.strip() for i in re.split('\s+', l.strip(), maxsplit = 1)]
                if _line[0] == 'account':
                    if re.match('^default\s?:\s?', _line[1]):  # it's the default account specifier
                        cfg['default'] = _line[1].split(':', maxsplit = 1)[1].strip()  
                    else:
                        if _line[1] not in cfg.keys():  # it's a new account definition
                            cfg[_line[1]] = {}
                            _acct = _line[1]
                    _defaults = False
                elif _line[0] == 'defaults':  # it's the defaults
                    _acct = 'defaults'
                else:  # it's a config directive
                    cfg[_acct][_line[0]] = _line[1]
            for a in list(cfg):
                if a != 'default':
                    for k, v in cfg['defaults'].items():
                        if k not in cfg[a].keys():
                            cfg[a][k] = v
            del(cfg['defaults'])
            return(cfg)

        def sendEmail(self, msg, key, profile):  # This needs way more parsing to support things like plain ol' port 25 plaintext (ugh), etc.
            if 'tls-starttls' in self.msmtp['cfg'][profile].keys() and self.msmtp['cfg'][profile]['tls-starttls'] == 'on':
                smtpserver = smtplib.SMTP(self.msmtp['cfg'][profile]['host'], int(self.msmtp['cfg'][profile]['port']))
                smtpserver.ehlo()
                smtpserver.starttls()
                # we need to EHLO twice with a STARTTLS because email is weird.
            elif self.msmtp['cfg'][profile]['tls'] == 'on':
                smtpserver = smtplib.SMTP_SSL(self.msmtp['cfg'][profile]['host'], int(self.msmtp['cfg'][profile]['port']))
            smtpserver.ehlo()
            smtpserver.login(self.msmtp['cfg'][profile]['user'], self.msmtp['cfg'][profile]['password'])
            smtpserver.sendmail(self.msmtp['cfg'][profile]['user'], key['pkey']['email'], msg.as_string())
            smtpserver.close()
            return()
        
    def postalWorker(self):
        m = self.Mailer()
        if 'KANT' in m.msmtp['cfg'].keys():
            _profile = 'KANT'
        else:
            _profile = m.msmtp['cfg']['default']  # TODO: let this be specified on the CLI args?
        if 'user' not in m.msmtp['cfg'][_profile].keys() or not m.msmtp['cfg'][_profile]['user']:
            return()  # We don't have MSMTP configured.
        # Reconstruct the keyserver list.
        _keyservers = []
        for k in self.args['keyservers']:
            _keyservers.append('{0}://{1}:{2}'.format(k['proto'], k['server'], k['port'][0]))
        # Export our key so we can attach it.
        _pubkeys = {}
        for e in ('asc', 'gpg'):
            if e == 'asc':
                self.ctx.armor = True
            else:
                self.ctx.armor = False
            _pubkeys[e] = gpg.Data()  # This is a data buffer to store your ASCII-armored pubkeys
            self.ctx.op_export_keys([self.mykey['pkey']['key']], 0, _pubkeys[e])
            _pubkeys[e].seek(0, 0)  # Read with e.g. _sigs['asc'].read()
        for k in list(self.keys.keys()):
            if self.keys[k]['notify']:
                _body = {}
                for t in list(self.tpls.keys()):
                    # There's gotta be a more efficient way of doing this...
                    #_tplenv = jinja2.Environment(loader = jinja2.BaseLoader()).from_string(self.tpls[t])
                    _tplenv = jinja2.Environment().from_string(self.tpls[t])
                    _body[t] = _tplenv.render(key = self.keys[k],
                                              mykey = self.mykey,
                                              keyservers = _keyservers)
                b = MIMEMultipart('alternative')  # Set up a body
                for c in _body.keys():
                    b.attach(MIMEText(_body[c], c))
                bmsg = MIMEMultipart()
                bmsg.attach(b)
                for s in _pubkeys.keys():
                    _attchmnt = MIMEApplication(_pubkeys[s].read(), '{0}.{1}'.format(self.mykey['pkey']['key'].fpr, s))
                    _attchmnt['Content-Disposition'] = 'attachment; filename="{0}.{1}"'.format(self.mykey['pkey']['key'].fpr, s)
                    bmsg.attach(_attchmnt)
                # Now we sign the body. This incomprehensible bit monkey-formats bmsg to be a multi-RFC-compatible
                # string, which is then passed to our gpgme instance's signing mechanishm, and the output of that is
                # returned as plaintext. Whew.
                self.ctx.armor = True
                
                _sig = self.ctx.sign((bmsg.as_string().replace('\n', '\r\n')).encode('utf-8'),
                                      mode = gpg.constants.SIG_MODE_DETACH)
                imsg = Message()  # Build yet another intermediate message...
                imsg['Content-Type'] = 'application/pgp-signature; name="signature.asc"'
                imsg['Content-Description'] = 'OpenPGP digital signature'
                imsg.set_payload(_sig[0].decode('utf-8'))
                msg = MIMEMultipart(_subtype = 'signed',
                                    micalg = "pgp-{0}".format(self.maps['hashalgos'][_sig[1].signatures[0].hash_algo]),
                                    protocol = 'application/pgp-signature')
                msg.attach(bmsg)  # Attach the body (plaintext, html, pubkey attachmants)
                msg.attach(imsg)  # Attach the isignature
                msg['To'] = self.keys[k]['pkey']['email']
                if 'from' in m.msmtp['cfg'][_profile].keys():
                    msg['From'] = m.msmtp['cfg'][_profile]['from']
                else:
                    msg['From'] = self.mykey['pkey']['email']
                msg['Subject'] = 'Your GnuPG/PGP key has been signed'
                msg['Openpgp'] = 'id={0}'.format(self.mykey['pkey']['key'].fpr)
                msg['Date'] = datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
                msg['User-Agent'] = 'KANT (part of the r00t^2 OpTools suite: https://git.square-r00t.net/OpTools)'
                m.sendEmail(msg, self.keys[k], _profile)  # Send the email
                for d in (msg, imsg, bmsg, b, _body, _tplenv):  # Not necessary, but it pays to be paranoid; we do NOT want leaks.
                    del(d)
        del(m)
        return()
    
    def saveResults(self):
        _cachedir = os.path.join(self.cfgdir, 'cache', datetime.datetime.utcnow().strftime('%Y.%m.%d_%H.%M.%S'))
        os.makedirs(_cachedir, exist_ok = True)
        for k in self.keys.keys():
            _keyout = self.keys[k]
            # We need to normalize the datetime objects and gpg objects to strings
            _keyout['pkey']['creation'] = str(self.keys[k]['pkey']['creation'])
            _keyout['pkey']['key'] = '<GPGME object>'
            for u in list(_keyout['uids'].keys()):
                _keyout['uids'][u]['updated'] = str(self.keys[k]['uids'][u]['updated'])
            for s in list(_keyout['subkeys'].keys()):
                _keyout['subkeys'][s] = str(self.keys[k]['subkeys'][s])
            _fname = os.path.join(_cachedir, '{0}.json'.format(k))
            with open(_fname, 'a') as f:
                f.write('{0}\n'.format(json.dumps(_keyout, sort_keys = True, indent = 4)))
            del(_keyout)
        # And let's grab a copy of our key in the state that it exists in currently
        _mykey = self.mykey        
        # We need to normalize the datetime objects and gpg objects to strings again
        _mykey['pkey']['creation'] = str(_mykey['pkey']['creation'])
        _mykey['pkey']['key'] = '<GPGME object>'
        for u in list(_mykey['uids'].keys()):
            _mykey['uids'][u]['updated'] = str(self.mykey['uids'][u]['updated'])
        for s in list(_mykey['subkeys'].keys()):
            _mykey['subkeys'][s] = str(self.mykey['subkeys'][s])
        with open(os.path.join(_cachedir, '_SIGKEY.json'), 'w') as f:
            f.write('{0}\n'.format(json.dumps(_mykey, sort_keys = True, indent = 4)))
        return()

    def serverParser(self, uri):
        # https://en.wikipedia.org/wiki/Key_server_(cryptographic)#Keyserver_examples
        _server = {}
        _urlobj = urllib.parse.urlparse(uri)
        _server['proto'] = _urlobj.scheme
        _lazy = False
        if not _server['proto']:
            _server['proto'] = 'hkp'  # Default
        _server['server'] = _urlobj.hostname
        if not _server['server']:
            _server['server'] = re.sub('^([A-Za-z]://)?(.+[^:][^0-9])(:[0-9]+)?$', '\g<2>', uri, re.MULTILINE)
            _lazy = True
        _server['port'] = _urlobj.port
        if not _server['port']:
            if _lazy:
                _p = re.sub('.*:([0-9]+)$', '\g<1>', uri, re.MULTILINE)
        _server['port'] = self.maps['proto'][_server['proto']]  # Default
        return(_server)

    def verifyArgs(self, locargs):
        ## Some pythonization...
        if not locargs['batch']:
            locargs['keys'] = [re.sub('\s', '', k) for k in locargs['keys'].split(',')]
        else:
            ## Batch file
            _batchfilepath = os.path.abspath(os.path.expanduser(locargs['keys']))
            if not os.path.isfile(_batchfilepath):
                raise ValueError('{0} does not exist or is not a regular file.'.format(_batchfilepath))
            else:
                with open(_batchfilepath, 'r') as f:
                    self.csvraw = f.readlines()
                locargs['keys'] = _batchfilepath
        locargs['keyservers'] = [re.sub('\s', '', s) for s in locargs['keyservers'].split(',')]
        locargs['keyservers'] = [self.serverParser(s) for s in locargs['keyservers']]
        ## Key(s) to sign
        locargs['rcpts'] = {}
        if not locargs['batch']:
            _keyiter = locargs['keys']
        else:
            _keyiter = []
            for row in csv.reader(self.csvraw, delimiter = ',', quotechar = '"'):
                _keyiter.append(row[0])
        for k in _keyiter:
            locargs['rcpts'][k] = {}
            try:
                int(k, 16)
                _ktype = 'fpr'
            except:  # If it isn't a valid key ID...
                if not re.match('^<?[\w\.\+\-]+\@[\w-]+\.[a-z]{2,3}>?$', k):  # is it an email address?
                    raise ValueError('{0} is not a valid email address'.format(k))
                else:
                    r = k.replace('<', '').replace('>', '')
                    locargs['rcpts'][r] = locargs['rcpts'][k]
                    if k != r:
                        del(locargs['rcpts'][k])
                    k = r
                    _ktype = 'email'
            locargs['rcpts'][k]['type'] = _ktype
            # Security is important. We don't want users getting collisions, so we don't allow shortened key IDs.
            if _ktype == 'fpr' and not len(k) == 40:
                raise ValueError('{0} is not a full 40-char key ID or key fingerprint'.format(k))
        ## Signing key
        if not locargs['sigkey']:
            raise ValueError('A key for signing is required') # We need a key we can sign with.
        else:
            if not os.path.lexists(locargs['gpgdir']):
                raise FileNotFoundError('{0} does not exist'.format(locargs['gpgdir']))
            elif os.path.isfile(locargs['gpgdir']):
                raise NotADirectoryError('{0} is not a directory'.format(locargs['gpgdir']))
            # Now we need to verify that the private key exists...
            try:
                _ctx = gpg.Context()
                _sigkey = _ctx.get_key(locargs['sigkey'], True)
            except gpg.errors.GPGMEError or gpg.errors.KeyNotFound:
                raise ValueError('Cannot use key {0}'.format(locargs['sigkey']))
            # And that it is an eligible candidate to use to sign.
            if not _sigkey.can_sign or True in (_sigkey.revoked, _sigkey.expired, _sigkey.disabled):
                raise ValueError('{0} is not a valid candidate for signing'.format(locargs['sigkey']))
        ## Keyservers
        if locargs['testkeyservers']:
            for s in locargs['keyservers']:
                # Test to make sure the keyserver is accessible.
                _v6test = socket(AF_INET6, SOCK_DGRAM)
                try:
                    _v6test.connect(('ipv6.square-r00t.net', 0))
                    _nettype = AF_INET6  # We have IPv6 intarwebz
                except:
                    _nettype = AF_INET  # No IPv6, default to IPv4
                for _proto in locargs['keyservers'][s]['port'][1]:
                    if _proto == 'udp':
                        _netproto = SOCK_DGRAM
                    elif _proto == 'tcp':
                        _netproto = SOCK_STREAM
                    _sock = socket(nettype, netproto)
                    _sock.settimeout(10)
                    _tests = _sock.connect_ex((locargs['keyservers'][s]['server'],
                                              int(locargs['keyservers'][s]['port'][0])))
                    _uristr = '{0}://{1}:{2} ({3})'.format(locargs['keyservers'][s]['proto'],
                                                           locargs['keyservers'][s]['server'],
                                                           locargs['keyservers'][s]['port'][0],
                                                           _proto.upper())
                    if not tests == 0:
                        raise OSError('Keyserver {0} is not available'.format(_uristr))
                    else:
                        print('Keyserver {0} is accepting connections.'.format(_uristr))
                    sock.close()
        return(locargs)
    
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
        for k in ctx.keylist(None, secret = True):  # "None" is query string; this grabs all keys in the private keyring
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
                      default = None,
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
    args.add_argument('-m',
                      '--msmtp',
                      dest = 'msmtp_profile',
                      default = None,
                      help = 'The msmtp profile to use to send the notification emails. See the man page for more information.')
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





def main():
    # This could be cleaner-looking, but we do it this way so the class can be used externally
    # with a dict instead of an argparser result.
    args = vars(parseArgs().parse_args())
    sess = SigSession(args)
    sess.modifyDirmngr('new')
    sess.buildKeys()
    sess.sigKeys()
    sess.trustKeys()
    sess.pushKeys()
    sess.postalWorker()
    sess.saveResults()
    sess.modifyDirmngr('old')

if __name__ == '__main__':
    main()
