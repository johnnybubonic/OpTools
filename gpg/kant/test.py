#!/usr/bin/env python3

# This is more of a documentation on some python-gpgme (https://pypi.python.org/pypi/gpg) examples.
# Because their only documentation for the python bindings is in pydoc, and the C API manual is kind of useless.

import gpg
import gpg.constants
import inspect
import pprint

# my key ID
mykey = '748231EBCBD808A14F5E85D28C004C2F93481F6B'
# a key to test with
theirkey = '63D1CEA387C27A92E0D50AB8343C305F9109D4DC'

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
ctx.keylist(pattern = 'bts@square-r00t.net',
            secret = False,
            mode = klmodes['both'],
            source = None)

# Test fetching from a keyserver

