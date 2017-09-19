#!/usr/bin/env python3

# This is less of a test suite and more of an active documentation on some python-gpgme (https://pypi.python.org/pypi/gpg) examples.
# Because their only documentation for the python bindings is in pydoc, and the C API manual is kind of useless.

import datetime
import gpg
import gpg.constants
import inspect
import jinja2
import os
import pprint
import re
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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
        out.seek(0, 0)
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
out.seek(0, 0)
#print(out.read(), end = '\n\n')

#Test sending to a keyserver
buf = gpg.Data()
ctx.op_export(tkey2.fpr, gpg.constants.EXPORT_MODE_EXTERN, None)

# Test writing the pubkey out to a file
buf = gpg.Data()
ctx.op_export_keys([tkey2], 0, buf)  # do i NEED to specify a mode?
buf.seek(0, 0)
with open('/tmp/pubkeytest.gpg', 'wb') as f:
    f.write(buf.read())
#del(buf)
# Let's also test writing out the ascii-armored..
ctx.armor = True
#buf = gpg.Data()
buf.seek(0, 0)
ctx.op_export_keys([tkey2], 0, buf)  # do i NEED to specify a mode?
buf.seek(0, 0)
#print(buf.read())
#buf.seek(0, 0)
with open('/tmp/pubkeytest.asc', 'wb') as f:
    f.write(buf.read())
del(buf)

# And lastly, let's test msmtprc
def getCfg(fname):
    cfg = {'default': None, 'defaults': {}}
    _defaults = False
    _acct = None
    with open(fname, 'r') as f:
        cfg_raw = f.read()
    for l in cfg_raw.splitlines():
        if re.match('^\s?(#.*|)$', l):
            continue  # skip over blank and commented lines
        line = [i.strip() for i in re.split('\s+', l.strip(), maxsplit = 1)]
        if line[0] == 'account':
            if re.match('^default\s?:\s?', line[1]):  # it's the default account specifier
                cfg['default'] = line[1].split(':', maxsplit = 1)[1].strip()  
            else:
                if line[1] not in cfg.keys():  # it's a new account definition
                    cfg[line[1]] = {}
                    _acct = line[1]
            _defaults = False
        elif line[0] == 'defaults':  # it's the defaults
            _acct = 'defaults'
        else:  # it's a config directive
            cfg[_acct][line[0]] = line[1]
    for a in list(cfg):
        if a != 'default':
            for k, v in cfg['defaults'].items():
                if k not in cfg[a].keys():
                    cfg[a][k] = v
    del(cfg['defaults'])
    return(cfg)
homeconf = os.path.join(os.environ['HOME'], '.msmtprc')
sysconf = '/etc/msmtprc'
msmtp = {'path': None}
if not os.path.isfile(homeconf):
    if not os.path.isfile(sysconf):
        msmtp['conf'] = False
    else:
        msmtp['conf'] = sysconf
else:
    msmtp['conf'] = homeconf
if os.path.isfile(msmtp['conf']):
    path = os.environ['PATH']
    for p in path.split(':'):
        fullpath = os.path.join(p, 'msmtp')
        if os.path.isfile(fullpath):
            msmtp['path'] = fullpath
            break  # break out the first instance of it we find since the shell parses PATH first to last and so do we
    if msmtp['path']:
        # Okay. So we have a config file, which we're assuming to be set up correctly, and a path to a binary.
        # Now we need to parse the config.
        msmtp['cfg'] = getCfg(msmtp['conf'])
pprint.pprint(msmtp)
if msmtp['path']:
    # Get the appropriate MSMTP profile
    profile = msmtp['cfg']['default']
    # Buuuut i use a different profile when i test, because i use msmtp for production-type stuff.
    #if os.environ['USER'] == 'bts':
    #    profile = 'gmailtesting'
    # Now we can try to send an email... yikes.
    ## First we set up the message templates.
    body_in = {'plain': None, 'html': None}
    body_in['plain'] = """Hello, person!

    This is a test message.

    Thanks."""
    body_in['html'] = """\
    <html>
        <head></head>
            <body>
            <p><b>Hi there, person!</b> This is a test email.</p>
            <p>It supports fun things like HTML.</p>
            <p>--<br><a href='https://games.square-r00t.net/'>https://games.square-r00t.net</a><br>
                Admin: <a href='mailto:bts@square-r00t.net'>r00t^2</a>
                </p>
            </body>
    </html>"""
    # Now, some attachments.
    part = {}
    ctx.armor = False
    buf = gpg.Data()
    ctx.op_export_keys([tkey2], 0, buf)
    buf.seek(0, 0)
    part['gpg'] = MIMEApplication(buf.read(), '{0}.gpg'.format(tkey2.fpr))
    part['gpg']['Content-Disposition'] = 'attachment; filename="{0}.gpg"'.format(tkey2.fpr)
    ctx.armor = True
    buf.seek(0, 0)
    ctx.op_export_keys([tkey2], 0, buf)
    buf.seek(0, 0)
    part['asc'] = MIMEApplication(buf.read(), '{0}.asc'.format(tkey2.fpr))
    part['asc']['Content-Disposition'] = 'attachment; filename="{0}.asc"'.format(tkey2.fpr)
    #msg = MIMEMultipart('alternative')
    msg = MIMEMultipart()
    msg['preamble'] = 'This is a multi-part message in MIME format.\n'
    msg['From'] = msmtp['cfg'][profile]['from']
    msg['To'] = msmtp['cfg'][profile]['from']  # to send to more than one:  ', '.join(somelist)
    msg['Date'] = datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
    msg['Subject'] = 'TEST EMAIL VIA TEST.PY'
    msg['epilogue'] = ''
    body = MIMEMultipart('alternative')
    body.attach(MIMEText(body_in['plain'], 'plain'))
    body.attach(MIMEText(body_in['html'], 'html'))
    msg.attach(body)
    for f in part.keys():
        msg.attach(part[f])

    # This needs way more parsing to support things like plain ol' port 25 plaintext (ugh), etc.
    if 'tls-starttls' in msmtp['cfg'][profile].keys() and msmtp['cfg'][profile]['tls-starttls'] == 'on':
        smtpserver = smtplib.SMTP(msmtp['cfg'][profile]['host'], int(msmtp['cfg'][profile]['port']))
        smtpserver.ehlo()
        smtpserver.starttls()
        # we need to EHLO again after a STARTTLS because email is weird.
    elif msmtp['cfg'][profile]['tls'] == 'on':
        smtpserver = smtplib.SMTP_SSL(msmtp['cfg'][profile]['host'], int(msmtp['cfg'][profile]['port']))
    smtpserver.ehlo()
    smtpserver.login(msmtp['cfg'][profile]['user'], msmtp['cfg'][profile]['password'])
    smtpserver.sendmail(msmtp['cfg'][profile]['user'], msg['To'], msg.as_string())
    smtpserver.close()
