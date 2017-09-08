#!/usr/bin/env python3

# This is less of a test suite and more of an active documentation on some python-gpgme (https://pypi.python.org/pypi/gpg) examples.
# Because their only documentation for the python bindings is in pydoc, and the C API manual is kind of useless.

import gpg
import gpg.constants
import inspect
import os
import pprint
import re
import subprocess
import operator
from functools import reduce

os.environ['GNUPGHOME'] = '/home/bts/tmpgpg'
# JUST in case we need to...
#subprocess.run(['gpgconf', '--reload', 'dirmngr'])

# my key ID
#mykey = '748231EBCBD808A14F5E85D28C004C2F93481F6B'
mykey = '2805EC3D90E2229795AFB73FF85BC40E6E17F339'
# a key to test with
theirkey = 'CA7D304ABA7A3E24C9414D32FFA0F1361AD82A06'
testfetch = [theirkey, '748231EBCBD808A14F5E85D28C004C2F93481F6B']

# Create a context
# Params:
#armor           -- enable ASCII armoring (default False)
#textmode        -- enable canonical text mode (default False)
#offline         -- do not contact external key sources (default False)
#signers         -- list of keys used for signing (default [])
#pinentry_mode   -- pinentry mode (default PINENTRY_MODE_DEFAULT)
#protocol        -- protocol to use (default PROTOCOL_OpenPGP)
#home_dir        -- state directory (default is the engine default)
ctx = gpg.Context()

# Fetch a key from the keyring
#secret          -- to request a secret key
mkey = ctx.get_key(mykey)
tkey = ctx.get_key(theirkey)

## Print the attributes of our key and other info
##https://stackoverflow.com/a/41737776
##for k in (mkey, tkey):
#for k in [mkey]:
#    for i in inspect.getmembers(k):
#        if not i[0].startswith('_'):
#            pprint.pprint(i)
#pprint.pprint(ctx.get_engine_info())

# Print the constants
#pprint.pprint(inspect.getmembers(gpg.constants))

# Get remote key. Use an OR to search both keyserver and local.
#ctx.set_keylist_mode(gpg.constants.KEYLIST_MODE_EXTERN|gpg.constants.KEYLIST_MODE_LOCAL)
klmodes = {'local': gpg.constants.KEYLIST_MODE_LOCAL,
           'remote': gpg.constants.KEYLIST_MODE_EXTERN,
           'both': gpg.constants.KEYLIST_MODE_LOCAL|gpg.constants.KEYLIST_MODE_EXTERN}

# List keys
#pattern -- return keys matching pattern (default: all keys)
#secret  -- return only secret keys (default: False)
#mode    -- keylist mode (default: list local keys)
#source  -- read keys from source instead from the keyring
#            (all other options are ignored in this case)
tkey2 = None

# jrdemasi@gmail.com = 0xEFD9413B17293AFDFE6EA6F1402A088DEDF104CB
for k in ctx.keylist(pattern = 'jrdemasi', secret = False, mode = klmodes['remote'], source = None):
    #pprint.pprint(inspect.getmembers(k))
    tkey2 = k
    #print(tkey2.fpr)

# Test fetching from a keyserver - we'll grab the last key from the above iteration
try:
    ctx.op_import_keys([tkey2])
except gpg.errors.GPGMEError:
    pass  # key isn't on the keyserver, or it isn't accessible, etc.

# Test signing
ctx.key_tofu_policy(tkey2, gpg.constants.TOFU_POLICY_ASK)
ctx.signers = [mkey]
days_valid = 4
exptime = 4 * 24 * 60 * 60
ctx.key_sign(tkey2, expires_in = exptime, local = True)

# https://www.apt-browse.org/browse/debian/wheezy/main/amd64/python-pyme/1:0.8.1-2/file/usr/share/doc/python-pyme/examples/t-edit.py
# https://searchcode.com/codesearch/view/20535820/
# https://git.gnupg.org/cgi-bin/gitweb.cgi?p=gnupg.git;a=blob;f=doc/DETAILS;h=0be55f4d64178a5636cbe9f12f63c6f9853f3aa2;hb=refs/heads/master
class KeyEditor(object):
    def __init__(self):
        self.replied_once = False
        trust = '3'  # this is the level of trust... in this case, marginal.
        rcptemail = 'test@test.com'
        # we exclude 'help'
        self.kprmpt = ['trust', 'fpr', 'sign', 'tsign', 'lsign', 'nrsign', 'grip', 'list',
                        'uid', 'key', 'check', 'deluid', 'delkey', 'delsig', 'pref', 'showpref',
                        'revsig', 'enable', 'disable', 'showphoto', 'clean', 'minimize', 'save',
                        'quit']
        self.prmpt = {'edit_ownertrust': {'value': trust,
                                          'set_ultimate': {'okay': 'yes'}},
                      'untrusted_key': {'override': 'yes'},
                      'pklist': {'user_id': {'enter': rcptemail}},
                      'keyedit': {'prompt': 'trust',  # the mode we initiate.
                                  'save': {'okay': 'yes'}}}

    def edit_fnc(self, status, args, out):
        result = None
        out.seek(0,0)
        #print(status, args)
        #print(out.read().decode('utf-8'))
        #print('{0} ({1})'.format(status, args))
        def mapDict(m, d):
            return(reduce(operator.getitem, m, d))
        if args == 'keyedit.prompt' and self.replied_once:
            result = 'quit'
        elif status == 'KEY_CONSIDERED':
            result = None
            self.replied_once = False
        elif status == 'GET_LINE':
            #print('DEBUG: looking up mapping...')
            self.replied_once = True
            _ilist = args.split('.')
            result = mapDict(_ilist, self.prmpt)
            if not result:
                result = None
        return(result)

# Test setting trust
out = gpg.Data()
ctx.interact(tkey2, KeyEditor().edit_fnc, sink = out, fnc_value = out)
out.seek(0,0)
#print(out.read(), end = ' ')
