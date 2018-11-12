#!/usr/bin/env python

import base64
import copy
import gpg
import grp
import json
import lzma
import os
import pwd
import re
from socket import gethostname
import sqlite3

# NOTE: The gpg homedir should be owned by the user *running autopkg*.
# Likely priv-dropping will only work for root.
#

dirs = ('cache', 'dest', 'gpg_homedir')
u_g_pairs = ('chown', 'build_user')
json_vals = ('chmod', )

blank_db = """
/Td6WFoAAATm1rRGAgAhARwAAAAQz1jM4H//AxNdACmURZ1gyBn4JmSIjib+MZX9x4eABpe77H+o
CX2bysoKzO/OaDh2QGbNjiU75tmhPrWMvTFue4XOq+6NPls33xRRL8eZoITBdAaLqbwYY2XW/V/X
Gx8vpjcBnpACjVno40FoJ1qWxJlBZ0PI/8gMoBr3Sgdqnf+Bqi+E6dOl66ktJMRr3bdZ5C9vOXAf
42BtRfwJlwN8NItaWtfRYVfXl+40D05dugcxDLY/3uUe9MSgt46Z9+Q9tGjjrUA8kb5K2fqWSlQ2
6KyF3KV1zsJSDLuaRkP42JNsBTgg6mU5rEk/3egdJiLn+7AupvWQ3YlKkeALZvgEKy75wdObf6QI
jY4qjXjxOTwOG4oou7lNZ3fPI5qLCQL48M8ZbOQoTAQCuArdYqJmBwT2rF86SdQRP4EY6TlExa4o
+E+v26hKhYXO7o188jlmGFbuzqtoyMB1y3UG+Hi2SjPDilD5o6f9fEjiHZm2FY6rkPb9Km4UFlH1
d2A4Wt4iGlciZBs0lFRPKkgHR4s7KHTMKuZyC08qE1B7FwvyBTBBYveA2UoZlKY7d22IbiiSQ3tP
JKhj8nf8EWcgHPt46Juo80l7vqqn6AviY7b1JZXICdiJMbuWJEyzTLWuk4qlUBfimP7k9IjhDFpJ
gEXdNgrnx/wr5CIbr1T5lI9vZz35EacgNA2bGxLA8VI0W9eYDts3BSfhiJOHWwLQPiNzJwd4aeM1
IhqgTEpk+BD0nIgSB3AAB+NfJJavoQjpv0QBA6dH52utA5Nw5L//Ufw/YKaA7ui8YQyDJ7y2n9L3
ugn6VJFFrYSgIe1oRkJBGRGuBgGNTS3aJmdFqEz1vjZBMkFdF+rryXzub4dst2Qh01E6/elowIUh
2whMRVDO28QjyS9tLtLLzfTmBk2NSxs4+znE0ePKKw3n/p6YlbPRAw24QR8MTCOpQ2lH1UZNWBM2
epxfmWtgO5b/wGYopRDEvDDdbPAq6+4zxTOT5RmdWZyc46gdizf9+dQW3wZ9iBDjh4MtuYPvLlqr
0GRmsyrxgFxkwvVoXASNndS0NPcAADkAhYCxn+W2AAGvBoCAAgB/TQWascRn+wIAAAAABFla
"""

def firstrun(dbfile):
    dbdata = lzma.decompress(base64.b64decode(blank_db))
    with open(dbfile, 'wb') as f:
        f.write(dbdata)
    return()

def main(connection, cursor):
    cfg = {'orig_cwd': os.getcwd(),
           'pkgpaths': []}
    cursor.execute("SELECT directive, value FROM config")
    for r in cursor.fetchall():
        cfg[r['directive']] = r['value'].strip()
    for k in cfg:
        for x in (True, False, None):
            if cfg[k] == str(x):
                cfg[k] = x
                break
        if k in json_vals:
            cfg[k] = json.loads(cfg[k])
        if k == 'path':
            paths = []
            for i in cfg[k].split(':'):
                p = os.path.abspath(os.path.expanduser(i))
                paths.append(p)
            cfg[k] = paths
        if k in dirs:
            if cfg[k]:
                cfg[k] = os.path.abspath(os.path.expanduser(cfg[k]))
                os.makedirs(cfg[k], exist_ok = True)
        if k in u_g_pairs:
            dflt = [pwd.getpwuid(os.geteuid()).pw_name, grp.getgrgid(os.getegid()).gr_name]
            l = re.split(':|\.', cfg[k])
            if len(l) == 1:
                l.append(None)
            for idx, i in enumerate(l[:]):
                if i in ('', None):
                    l[idx] = dflt[idx]
            cfg[k] = {}
            cfg[k]['uid'] = (int(l[0]) if l[0].isnumeric() else pwd.getpwnam(l[0]).pw_uid)
            cfg[k]['gid'] = (int(l[1]) if l[1].isnumeric() else grp.getgrnam(l[1]).gr_gid)
    cfg['orig_user'] = {'uid': os.geteuid(),
                        'gid': os.getegid()}
    # Ugh. https://orkus.wordpress.com/2011/04/17/python-getting-umask-without-change/
    cfg['orig_user']['umask'] = os.umask(0)
    os.umask(cfg['orig_user']['umask'])
    cfg['orig_user']['groups'] = os.getgroups()
    for i in cfg['chmod']:
        cfg['chmod'][i] = int(cfg['chmod'][i], 8)
    cfg['orig_user']['env'] = copy.deepcopy(dict(os.environ))
    os.chown(cfg['cache'], uid = cfg['build_user']['uid'], gid = cfg['build_user']['gid'])
    os.chown(cfg['dest'], uid = cfg['chown']['uid'], gid = cfg['chown']['gid'])
    return(cfg)

def GPG(cur, homedir = None, keyid = None):
    g = gpg.Context(home_dir = homedir)
    if not keyid:
        # We don't have a key specified, so we need to generate one and update the config.
        s = ('This signature and signing key were automatically generated using Autopkg from OpTools: '
             'https://git.square-r00t.net/OpTools/')
        g.sig_notation_add('automatically-generated@git.square-r00t.net', s, gpg.constants.sig.notation.HUMAN_READABLE)
        userid = 'Autopkg Signing Key ({0}@{1})'.format(os.getenv('SUDO_USER', os.environ['USER']), gethostname())
        params = {
            #'algorithm': 'ed25519',
            'algorithm': 'rsa4096',
            'expires': False,
            'expires_in': 0,
            'sign': True,
            'passphrase': None
            }
        keyid = g.create_key(userid, **params).fpr
        # https://stackoverflow.com/a/50718957
        q = {}
        for col in ('keyid', 'homedir'):
            if sqlite3.sqlite_version_info > (3, 24, 0):
                q[col] = ("INSERT INTO config (directive, value) "
                          "VALUES ('gpg_{0}', ?) "
                          "ON CONFLICT (directive) "
                          "DO UPDATE SET value = excluded.value").format(col)
            else:
                cur.execute("SELECT id FROM config WHERE directive = 'gpg_{0}'".format(col))
                row = cur.fetchone()
                if row:
                    q[col] = ("UPDATE config SET value = ? WHERE id = '{0}'").format(row['id'])
                else:
                    q[col] = ("INSERT INTO config (directive, value) VALUES ('gpg_{0}', ?)").format(col)
            cur.execute(q[col], (locals()[col], ))
    return(keyid, g)
