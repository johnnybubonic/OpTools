#!/usr/bin/env python3

import argparse
import getpass
import hashlib
import os
import pprint
import sqlite3
import subprocess
import sys

class Manager(object):
    def __init__(self, args):
        self.args = args
        self.conn = self.connect()
        self.conn.row_factory = sqlite3.Row
        if 'interactive' not in self.args.keys():
            self.args['interactive'] = False
        # Key mappings/types in user_info table; thanks to DireFog in Mumble's IRC channel for help with this.
        # src/murmur/ServerDB.h, enum UserInfo
        # 0 = User_Name
        # 1 = User_Email
        # 2 = User_Comment
        # 3 = User_Hash
        # 4 = User_Password
        # 5 = User_LastActive
        # 6 = User_KDFIterations
        self.infomap = {0: 'name',
                        1: 'email',
                        2: 'comment',
                        3: 'certhash',
                        4: 'password',
                        5: 'last_active',
                        6: 'kdf_iterations'}

    def connect(self):
        if not os.path.isfile(self.args['database']):
            raise FileNotFoundError('{0} does not exist! Check your path or create the initial databse by running murmurd.')
        conn = sqlite3.connect(self.args['database'])
        return(conn)

    def add(self):
        # SQLDO("INSERT INTO `%1users`... in src/murmur/ServerDB.cpp
        if not (self.args['certhash'] or self.args['password']):
            raise RuntimeError('You must specify either a certificate hash or a method for getting the password.')
        if self.args['certhash']:  # it's a certificate fingerprint hash
            _e = '{0} is not a valid certificate fingerprint hash.'.format(self.args['certhash'])
            try:
                # Try *really hard* to mahe sure it's a SHA1.
                # SHA1s are 160 bits in length, in hex (the string representations are
                # 40 chars). However, we use 162 because of the prefix python3 adds
                # automatically: "0b".
                h = int(self.args['certhash'], 16)
                try:
                    assert len(bin(h)) == 162
                except AssertionError:
                    raise ValueError(_e)
            except (ValueError, TypeError):
                raise ValueError(_e)
        if self.args['password']:  # it's a password
            if self.args['password'] == 'stdin':
                self.args['password'] = hashlib.sha1(sys.stdin.read().replace('\n', '').encode('utf-8')).hexdigest().lower()
            else:
                _repeat = True
                while _repeat == True:
                    _pass_in = getpass.getpass('What password should {0} have (will not echo back)? ')
                    if not _pass_in or _pass_in == '':
                        print('Invalid password. Please re-enter: ')
                    else:
                        self.args['password'] = hashlib.sha1(_pass_in.replace('\n', '').encode('utf-8')).hexdigest().lower()
        # Insert into the "users" table
        # I spit on the Mumble developers for not using https://sqlite.org/autoinc.html.
        # Warning: this is kind of dangerous, as you can hit a race condition here.
        _cur = self.conn.cursor()
        _cur.execute("SELECT user_id FROM users WHERE server_id = '{0}'".format(self.args['server']))
        _used_ids = [i[0] for i in _cur.fetchall()]
        _used_ids2 = [x for x in range(_used_ids[0], _used_ids[-1] + 1)]
        _avail_uids = list(set(_used_ids) ^ set(_used_ids2))
        _qinsert = {}
        _qinsert['lastchannel'] = '0'
        _qinsert['last_active'] = None  # Change this to '' if it complains
        _qinsert['texture'] = None  # Change this to '' if it complains
        _qinsert['uid'] = _avail_uids[0]
        for k in ('username', 'server', 'password'):
            _qinsert[k] = self.args[k]
        for k in _qinsert.keys():
            if not _qinsert[k]:
                _qinsert[k] = ''
        _q = ("INSERT INTO users (server_id, user_id, name, pw, lastchannel, texture, last_active) " +
              "VALUES ('{server}', '{uid}', '{username}', '{password}', '{lastchannel}', '{texture}'," +
              "'{last_active}')").format(**_qinsert)
        _cur.execute(_q)
        self.conn.commit()
        # Insert into the "user_info" table
        for c in ('name', 'email', 'certhash', 'comment'):
            if self.args[c]:
                _qinsert = {}
                _qinsert['server'] = self.args['server']
                _qinsert['user_id'] = _avail_uids[0]
                _qinsert['keyid'] = list(self.infomap.keys())[list(self.infomap.values()).index(c)]
                _qinsert['value'] = self.args[c]
                _q = ("INSERT INTO user_info (server_id, user_id, key, value) " +
                      "VALUES ('{server}', '{user_id}', '{keyid}', '{value}')".format(**_qinsert))
                _cur.execute(_q)
                self.conn.commit()
        _cur.close()
        # Insert into the "group_members" table if we need to
        if self.args['groups']:
            # The groups table, thankfully, has autoincrement.
            for g in self.args['groups']:
                _ginfo = {}
                _minsert = {'server': self.args['server'],
                            'uid': _avail_uids[0],
                            'addit': 1}
                _ginsert = {'server': self.args['server'],
                            'name': g,
                            'chan_id': 0,
                            'inherit': 1,
                            'inheritable': 1}
                _create = True
                _cur = self.conn.cursor()
                _q = "SELECT * FROM groups WHERE server_id = '{0}'".format(self.args['server'])
                _cur.execute(_q)
                for r in _cur.fetchall():
                    if r['name'] == g:
                        _create = False
                        _ginfo = r
                        break
                if not _ginfo:
                    create = True  # Just in case...
                if _create:
                    _q = ("INSERT INTO groups (server_id, name, channel_id, inherit, inheritable) " +
                          "VALUES ('{server}', '{name}', '{chan_id}', '{inherit}', '{inheritable}')").format(**_ginsert)
                    _cur.execute(_q)
                    self.conn.commit()
                    _lastins = _cur.lastrowid
                    _q = ("SELECT * FROM groups WHERE group_id = '{0}' AND server_id = '{1}'").format(_lastins,
                                                                                                      self.args['server'])
                    _cur.execute(_q)
                    _ginfo = _cur.fetchone()
                _minsert['gid'] = _ginfo['group_id']
                _q = ("INSERT INTO group_members (group_id, server_id, user_id, addit) " +
                      "VALUES ('{gid}', '{server}', '{uid}', '{addit}')").format(**_minsert)
                _cur.execute(_q)
                self.conn.commit()
                _cur.close()
        return()

    def rm(self):
        _cur = self.conn.cursor()
        # First we'll need the user's UID.
        _q = "SELECT user_id FROM users WHERE server_id = '{0}' AND name = '{1}'".format(self.args['server'],
                                                                                         self.args['username'])
        _cur.execute(_q)
        _uid = _cur.fetchone()[0]
        # Then we get the groups the user's in; we'll need these in a bit.
        _q = "SELECT group_id FROM group_members WHERE server_id = '{0}' AND user_id = '{0}'".format(self.args['server'],
                                                                                                     _uid)
        _cur.execute(_q)
        _groups = [g[0] for g in _cur.fetchall()]
        # Okay, now we can delete the user and their metadata...
        _qtmpl = "DELETE FROM {0} WHERE server_id = '{1}' AND user_id = '{2}'"
        for t in ('users', 'group_members'):
            _q = _qtmpl.format(t, self.args['server'], _uid)
            _cur.execute(_q)
            self.conn.commit()
        if not self.args['noprune']:
            for t in ('user_info', 'acl'):
                _q = _qtmpl.format(t, self.args['server'], _uid)
                _cur.execute(_q)
                self.conn.commit()
        # Now some groups maintenance.
        if self.args['prunegrps']:
            for gid in _groups:
                _q = ("SELECT COUNT(*) FROM group_members WHERE " +
                      "server_id = '{0}' AND group_id = '{1}'").format(self.args['server'],
                                                                       gid)
                _cur.execute(_q)
                if _cur.fetchone()[0] == 0:
                    _q = ("DELETE FROM group_members WHERE " +
                          "server_id = '{0}' AND group_id = '{1}'").format(self.args['server'],
                                                                           gid)
                    _cur.execute(_q)
                    self.conn.commit()
        _cur.close()
        return()

    def lsUsers(self):
        users = {}
        _fields = ('server_id', 'user_id', 'name', 'pw', 'lastchannel', 'texture', 'last_active')
        if self.args['server']:
            try:
                self.args['server'] = int(self.args['server'])
                _q = "SELECT * FROM users WHERE server_id = '{0}'".format(self.args['server'])
            except (ValueError, TypeError):
                pass  # It's set as None, which we'll parse to mean as "all" per the --help output.
        else:
            _q = 'SELECT * FROM users'
        _cur = self.conn.cursor()
        _cur.execute(_q)
        for r in _cur.fetchall():
            _usr = r['user_id']
            users[_usr] = {}
            for f in _fields:
                if f != 'user_id':  # We set the dict key as this
                    users[_usr][f] = r[f]
            _q = "SELECT * FROM user_info WHERE server_id = '{0}' AND user_id = '{1}'".format(r['server_id'],
                                                                                              r['user_id'])
            _cur2 = self.conn.cursor()
            _cur2.execute(_q)
            for r2 in _cur2.fetchall():
                if r2['key'] in self.infomap.keys():
                    users[_usr][self.infomap[r2['key']]] = r2['value']
            _cur2.close()
            for k in self.infomap.keys():
                if self.infomap[k] not in users[_usr].keys():
                    users[_usr][self.infomap[k]] = None
            if users[_usr]['comment']:
                users[_usr]['comment'] = ('(truncated)' if len(users[_usr]['comment']) >= 32 else users[_usr]['comment'])
        _cur.close()
        #pprint.pprint(users)
        # Now we print (or just return) the results. Whew.
        if not self.args['interactive']:
            return(users)
        print_tmpl = ('{0:6}\t{1:3}\t{2:12} {3:24} {4:40} {5:40} {6:12} ' +
               '{7:19}   {8:32}')
        print(print_tmpl.format('Server','UID','Username','Email',
                                'Password', 'Certhash', 'Last Channel',
                                'Last Active', 'Comment'), end = '\n\n')
        for uid in users.keys():
            d = users[uid]
            print(print_tmpl.format(int(d['server_id']),
                                    int(uid),
                                    str(d['name']),
                                    str(d['email']),
                                    str(d['pw']),
                                    str(d['certhash']),
                                    (str(d['lastchannel']) if not d['lastchannel'] else int(d['lastchannel'])),
                                    str(d['last_active']),
                                    str(d['comment'])))
        return()

    def lsGroups(self):
        groups = {}
        _cur = self.conn.cursor()
        # First, we get the groups.
        if self.args['server']:
            _q = "SELECT * FROM groups WHERE server_id = '{0}'".format(self.args['server'])
        else:
            _q = "SELECT * FROM groups"
        _cur.execute(_q)
        for r in _cur.fetchall():
            _gid = r['group_id']
            groups[_gid] = {'server': r['server_id'],
                            'name': r['name'],
                            'chan_id': r['channel_id'],
                            'inherit': r['inherit'],
                            'inheritable': r['inheritable']}
            groups[_gid]['members'] = {}
            _cur2 = self.conn.cursor()
            _q2 = "SELECT * FROM group_members WHERE group_id = '{0}' AND server_id = '{1}'".format(_gid,
                                                                                                    groups[_gid]['server'])
            _cur2.execute(_q2)
            for r2 in _cur2.fetchall():
                # True means they are a member of the group. False means they are excluded from the group.
                # (Helps override default policies?)
                groups[_gid]['members'][r2['user_id']] = (True if r2['addit'] else False)
            _cur2.close()
        _cur.close()
        # Return if we're non-interactive...
        if not self.args['interactive']:
            return(groups)
        # Print the groups
        print('GROUPS:')
        print_tmpl = ('{0:3}\t{1:16}\t{2:10}\t{3:35}\t{4:30}')
        print(print_tmpl.format('GID', 'Name', 'Channel ID',
                                'Inherit Parent Channel Permissions?', 'Allow Sub-channels to Inherit?'), end = '\n\n')
        for g in groups.keys():
            d = groups[g]
            print(print_tmpl.format(g,
                                    d['name'],
                                    d['chan_id'],
                                    str(True if d['inherit'] == 1 else False),
                                    str(True if d['inheritable'] == 1 else False)))
        print('\n\nMEMBERSHIPS:')
        # And print the members
        print_tmpl = ('\t\t{0:3}\t{1:>19}')  # UID, Include or Exclude?
        for g in groups.keys():
            d = groups[g]
            print('{0} ({1}):'.format(d['name'], g))
            if d['members']:
                print(print_tmpl.format('UID', 'Include or Exclude?'), end = '\n\n')
                for m in d['members'].keys():
                    print(print_tmpl.format(m, ('Include' if d['members'][m] == 1 else 'Exclude')))
            else:
                print('\t\tNo members found; group is empty.')
        return()

    def edit(self):
        print('Editing is not currently supported.')
        return()

    def close(self):
        self.conn.close()
        if self.args['operation'] in ('add', 'rm', 'edit'):
            _cmd = ['systemctl', 'restart', 'murmur']
            subprocess.run(_cmd)
        return()

def parseArgs():
    _db = '/var/lib/murmur/murmur.sqlite'
    commonargs = argparse.ArgumentParser(add_help = False)
    reqcommon = commonargs.add_argument_group('REQUIRED common arguments')
    reqcommon.add_argument('-u',
                           '--user',
                           type = str,
                           dest = 'username',
                           required = True,
                           help = 'The username to perform the action for.')
    reqcommon.add_argument('-s',
                           '--server',
                           type = int,
                           dest = 'server',
                           default = 1,
                           help = 'The server ID. Defaults to \033[1m{0}\033[0m'.format(1))
    commonargs.add_argument('-d',
                            '--database',
                            type = str,
                            dest = 'database',
                            metavar = '/path/to/murmur.sqlite3',
                            default = _db,
                            help = 'The path to the sqlite3 database for Murmur. Default: \033[1m{0}\033[0m'.format(_db))
    args = argparse.ArgumentParser(epilog = 'This program has context-sensitive help (e.g. try "... add --help")')
    subparsers = args.add_subparsers(help = 'Operation to perform',
                                     dest = 'operation')
    addargs = subparsers.add_parser('add',
                                    parents = [commonargs],
                                    help = 'Add a user to the Murmur database')
    delargs = subparsers.add_parser('rm',
                                    parents = [commonargs],
                                    help = 'Remove a user from the Murmur database')
    listargs = subparsers.add_parser('ls',
                                     help = 'List users in the Murmur database')
    editargs = subparsers.add_parser('edit',
                                     parents = [commonargs],
                                     help = 'Edit a user in the Murmur database')
    # Operation-specific optional arguments
    addargs.add_argument('-n',
                         '--name',
                         type = str,
                         metavar = '"Firstname Lastname"',
                         dest = 'name',
                         default = None,
                         help = 'The new user\'s (real) name')
    addargs.add_argument('-c',
                         '--comment',
                         type = str,
                         metavar = '"This comment becomes the user\'s profile."',
                         dest = 'comment',
                         default = None,
                         help = 'The comment for the new user')
    addargs.add_argument('-e',
                         '--email',
                         type = str,
                         metavar = 'email@domain.tld',
                         dest = 'email',
                         default = None,
                         help = 'The email address for the new user')
    addargs.add_argument('-C',
                         '--certhash',
                         type = str,
                         metavar = 'CERTIFICATE_FINGERPRINT_HASH',
                         default = None,
                         dest = 'certhash',
                         help = ('The certificate fingerprint hash. See genfprhash.py. ' +
                                 'If you do not specify this, you must specify -p/--passwordhash'))
    addargs.add_argument('-p',
                         '--passwordhash',
                         type = str,
                         dest = 'password',
                         choices = ['stdin', 'prompt'],
                         default = None,
                         help = ('If not specified, you must specify -C/--certhash. Otherwise, either ' +
                                 '\'stdin\' (the password is being piped into this program) or \'prompt\' ' +
                                 '(a password will be asked for in a non-echoing prompt). "prompt" is much more secure and recommended.'))
    addargs.add_argument('-g',
                         '--groups',
                         type = str,
                         metavar = 'GROUP1(,GROUP2,GROUP3...)',
                         default = None,
                         help = ('A comma-separated list of groups the user should be added to. If a group ' +
                                 'doesn\'t exist, it will be created'))
    # Listing should only take the DB as the "common" arg
    listargs.add_argument('-g',
                          '--groups',
                          action = 'store_true',
                          dest = 'groups',
                          help = 'If specified, list groups (and their members), not users')
    listargs.add_argument('-s',
                           '--server',
                           type = str,
                           dest = 'server',
                           default = None,
                           help = 'The server ID. Defaults to all servers. Specify one by the numerical ID.')
    listargs.add_argument('-d',
                          '--database',
                          type = str,
                          dest = 'database',
                          metavar = '/path/to/murmur.sqlite3',
                          default = _db,
                          help = 'The path to the sqlite3 database for Murmur. Default: \033[1m{0}\033[0m'.format(_db))
    # Deleting args
    delargs.add_argument('-n',
                         '--no-prune',
                         dest = 'noprune',
                         action = 'store_true',
                         help = ('If specified, do NOT remove the ACLs and user info for the user as well (profile, ' +
                                 'certificate fingerprint, etc.)'))
    delargs.add_argument('-P',
                         '--prune-groups',
                         dest = 'prunegrps',
                         action = 'store_true',
                         help = 'If specified, remove any groups the user was in that are now empty (i.e. the user was the only member)')
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    if not args['operation']:
        #raise RuntimeError('You must specify an operation to perform. Try running with -h/--help.')
        exit('You must specify an operation to perform. Try running with -h/--help.')
    args['interactive'] = True
    #pprint.pprint(args)
    mgmt = Manager(args)
    if args['operation'] == 'add':
        if args['groups']:
            mgmt.args['groups'] = [g.strip() for g in args['groups'].split(',')]
        mgmt.add()
    elif args['operation'] == 'rm':
        mgmt.rm()
    elif args['operation'] == 'ls':
        if not args['groups']:
            mgmt.lsUsers()
        else:
            mgmt.lsGroups()
    elif args['operation'] == 'edit':
        mgmt.edit()
    else:
        pass  # No-op because something went SUPER wrong.
    mgmt.close()

if __name__ == '__main__':
    main()
