#!/usr/bin/env python3
# Thanks to https://github.com/alfg/murmur-rest/blob/master/app/__init__.py

import argparse
from collections import defaultdict
import configparser
import datetime
import email.utils
import getpass
import hashlib
import Ice  # python-zeroc-ice in AUR
import IcePy  # python-zeroc-ice in AUR
import getpass
import os
import re
import sys
import tempfile


class IceMgr(object):
    def __init__(self, args):
        self.args = args
        if 'interactive' not in self.args.keys():
            self.args['interactive'] = False
        if self.args['verbose']:
            import pprint
        self.getCfg()
        if self.cfg['MURMUR']['connection'] == '':
            self.cfg['MURMUR']['connection'] == 'ice'
        self.connect(self.cfg['MURMUR']['connection'])

    def getCfg(self):
        _cfg = os.path.join(os.path.abspath(os.path.expanduser(self.args['cfgfile'])))
        if not os.path.isfile(_cfg):
            raise FileNotFoundError('{0} does not exist!'.format(_cfg))
            return()
        _parser = configparser.ConfigParser()
        _parser._interpolation = configparser.ExtendedInterpolation()
        _parser.read(_cfg)
        self.cfg = defaultdict(dict)
        for section in _parser.sections():
            self.cfg[section] = {}
            for option in _parser.options(section):
                self.cfg[section][option] = _parser.get(section, option)
        return()

    def connect(self, ctxtype):
        ctxtype = ctxtype.strip().upper()
        if ctxtype.lower() not in ('ice', 'grpc'):
            raise ValueError('You have specified an invalid connection type.')
        _cxcfg = self.cfg[ctxtype]
        self.cfg[ctxtype]['spec'] = os.path.join(os.path.abspath(os.path.expanduser(self.cfg[ctxtype]['spec'])))
        # ICE START
        _props = {'ImplicitContext': 'Shared',
                  'Default.EncodingVersion': '1.0',
                  'MessageSizeMax': str(self.cfg['ICE']['max_size'])}
        _prop_data = Ice.createProperties()
        for k, v in _props.items():
            _prop_data.setProperty('Ice.{0}'.format(k), v)
        _conn = Ice.InitializationData()
        _conn.properties = _prop_data
        self.ice = Ice.initialize(_conn)
        _host = 'Meta:{0} -h {1} -p {2} -t 1000'.format(self.cfg['ICE']['proto'],
                                                        self.cfg['ICE']['host'],
                                                        self.cfg['ICE']['port'])
        _ctx = self.ice.stringToProxy(_host)
        # I owe a lot of neat tricks here to:
        # https://raw.githubusercontent.com/mumble-voip/mumble-scripts/master/Helpers/mice.py
        # Namely, the load-slice-from-server stuff especially
        _slicedir = Ice.getSliceDir()
        if not _slicedir:
            _slicedir = ["-I/usr/share/Ice/slice", "-I/usr/share/slice"]
        else:
            _slicedir = ['-I' + _slicedir]
        if self.cfg['ICE']['slice'] == '':
            if IcePy.intVersion() < 30500:
                # Old 3.4 signature with 9 parameters
                _op = IcePy.Operation('getSlice',
                                      Ice.OperationMode.Idempotent,
                                      Ice.OperationMode.Idempotent,
                                      True,
                                      (), (), (),
                                      IcePy._t_string, ())
            else:
                # New 3.5 signature with 10 parameters.
                _op = IcePy.Operation('getSlice',
                                      Ice.OperationMode.Idempotent,
                                      Ice.OperationMode.Idempotent,
                                      True,
                                      None,
                                      (), (), (),
                                      ((), IcePy._t_string, False, 0),
                                      ())
            _slice = _op.invoke(_ctx,
                                ((), None))
            (_filedesc, _filepath)  = tempfile.mkstemp(suffix = '.ice')
            _slicefile = os.fdopen(_filedesc, 'w')
            _slicefile.write(_slice)
            _slicefile.flush()
            Ice.loadSlice('', _slicedir + [_filepath])
            _slicefile.close()
            os.remove(_filepath)
        else:  # A .ice file was explicitly defined in the cfg
            _slicedir.append(self.cfg[ctxtype]['spec'])
            Ice.loadSlice('', _slicedir)
        import Murmur
        self.conn = {}
        if self.cfg['AUTH']['read'] != '':
            _secret = self.ice.getImplicitContext().put("secret",
                                                        self.cfg['AUTH']['read'])
            self.conn['read'] = Murmur.MetaPrx.checkedCast(_ctx)
        else:
            self.conn['read'] = False
        if self.cfg['AUTH']['write'] != '':
            _secret = self.ice.getImplicitContext().put("secret",
                                                        self.cfg['AUTH']['write'])
            self.conn['write'] = Murmur.MetaPrx.checkedCast(_ctx)
        else:
            self.conn['write'] = False
        return()

    def dictify(self, obj):
        # Thanks to:
        # https://github.com/alfg/murmur-rest/blob/master/app/utils.py
        # (Modified to be python 3 compatible)
        _rv = {'_type': str(type(obj))}
        if type(obj) in (bool, int, float, str, bytes):
            return(obj)
        if type(obj) in (list, tuple):
            return([dictify(i) for i in obj])
        if type(obj) == dict:
            return(dict((str(k), dictify(v)) for k, v in obj.items()))
        return(dictify(obj.__dict__))

    def add(self):
        _userinfo = {Murmur.UserInfo.UserName: self.args['UserName']}
        if not self.conn['write']:
            raise PermissionError('You do not have write access configured!')
        if not (self.args['certhash'] or self.args['password']):
            raise RuntimeError(('You must specify either a certificate hash ' +
                                 'or a method for getting the password.'))
        if self.args['certhash']:  # it's a certificate fingerprint hash
            _e = '{0} is not a valid certificate fingerprint hash.'.format(self.args['certhash'])
            try:
                # Try *really hard* to mahe sure it's a SHA1.
                # SHA1s are 160 bits in length, in binary representation.
                # (the string representations are 40 chars in hex).
                # However, we use 161 because of the prefix python3 adds
                # automatically: "0b". I know. "This should be 162!" Shut up, trust me.
                # Change it to 162 and watch it break if you don't believe me.
                h = int(self.args['certhash'], 16)
                try:
                    assert len(bin(h)) == 161
                    #_userinfo[Murmur.UserInfo.UserPassword] = None
                    _userinfo[Murmur.UserInfo.UserHash] = self.args['UserHash']
                except AssertionError:
                    raise ValueError(_e)
            except (ValueError, TypeError):
                raise ValueError(_e)
        if self.args['UserPassword']:  # it's a password
            if self.args['UserPassword'] == 'stdin':
                #self.args['password'] = hashlib.sha1(sys.stdin.read().replace('\n', '').encode('utf-8')).hexdigest().lower()
                _userinfo[Murmur.UserInfo.UserPassword] = sys.stdin.read().replace('\n', '').encode('utf-8')
                #_userinfo[Murmur.UserInfo.UserHash] = None
            else:
                _repeat = True
                while _repeat == True:
                    _pass_in = getpass.getpass('What password should {0} have (will not echo back)? '.format(self.args['UserName']))
                    if not _pass_in or _pass_in == '':
                        print('Invalid password. Please re-enter: ')
                    else:
                        _repeat = False
                        #self.args['password'] = hashlib.sha1(_pass_in.replace('\n', '').encode('utf-8')).hexdigest().lower()
                        _userinfo[Murmur.UserInfo.UserPassword] = _pass_in.replace('\n', '').encode('utf-8')
                        #_userinfo[Murmur.UserInfo.UserHash] = None
        # Validate the email address
        if self.args['UserEmail']:
            _email = email.utils.parseaddr(self.args['UserEmail'])
            # This is a stupidly simplified regex. For reasons why, see:
            # https://stackoverflow.com/questions/8022530/python-check-for-valid-email-address
            # http://www.regular-expressions.info/email.html
            # TL;DR: email is really fucking hard to regex against,
            # even (especially) if you follow RFC5322, and I don't want to have
            # to rely on https://pypi.python.org/pypi/validate_email
            if not re.match('[^@]+@[^@]+\.[^@]+', _email[1]):
                raise ValueError('{0} is not a valid email address!'.format(self.args['UserEmail']))
            else:
                _userinfo[Murmur.UserInfo.UserEmail] = _email[1]
        #else:
        #    _userinfo[Murmur.UserInfo.UserEmail] = None
        if self.args['UserComment']:
            _userinfo[Murmur.UserInfo.UserComment] = self.args['UserComment']
        # Set a dummy LastActive
        _userinfo[Murmur.UserInfo.LastActive] = str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        # Now we Do the Thing(TM)
        _server = self.conn['write'].getServer(self.args['server'])
        _regid = _server.registerUser(_userinfo)
        # And a little more Doing the Thing(TM), add groups.
        # This is... a little convoluted.
        # See https://sourceforge.net/p/mumble/discussion/492607/thread/579de8f9/
        if args['groups']:
            # First we get the ACL listings. The groups are *actually stored in
            # the ACLs*, which is... insane to me, sort of, but whatever.
            _acl = _server.getACL()
            # Then build a dict of all groups to assign.
            _groups = {}
            for g in self.args['groups'].split(','):
                _g = g.strip().split(':')
                if _g[0] not in _groups.keys():
                    _groups[_g[0]] = [g[1]]
                else:
                    _groups[_g[0]].append(_g[1])
            # Now we need to see which groups currently exist and which down't.
        if sys.stdout.isatty():
            print('Added user {0} (UID: {1})'.format(self.args['UserName'],
                                                     _regid))
            if self.args['verbose']:
                _u = _server.getRegistration(_regid)
                pprint.pprint(self.dictify(_u))

        return()

    def rm(self):
        pass

    def lsUsers(self):
        pass

    def lsGroups(self):
        pass

    def edit(self):
        pass

    def status(self):
        # https://github.com/alfg/murmur-rest/blob/master/app/api.py#L71
        pass

    def close(self):
        self.ice.destroy()
        if self.cfg['TUNNEL']['enable'].lower() in ('', 'true'):
            self.ssh.stop()
            self.ssh.close()
        return()

def parseArgs():
    _cfgfile = os.path.abspath(os.path.join(os.path.expanduser('~'),
                                            '.config',
                                            'optools',
                                            'mumbleadmin.ini'))
    commonargs = argparse.ArgumentParser(add_help = False)
    reqcommon = commonargs.add_argument_group('REQUIRED common arguments')
    optcommon = argparse.ArgumentParser(add_help = False)
    reqcommon.add_argument('-u', '--user',
                           type = str,
                           dest = 'UserName',
                           required = True,
                           help = 'The username to perform the action for.')
    reqcommon.add_argument('-s', '--server',
                           type = int,
                           dest = 'server',
                           default = 1,
                           help = ('The server ID. ' +
                                   'Defaults to \033[1m{0}\033[0m').format(1))
    optcommon.add_argument('-f', '--config',
                           type = str,
                           dest = 'cfgfile',
                           metavar = '/path/to/mumbleadmin.ini',
                           default = _cfgfile,
                           help = ('The path to the configuration file ' +
                                   '("mumleadmin.ini"). Default: \033[1m{0}\033[0m').format(_cfgfile))
    optcommon.add_argument('-v', '--verbose',
                           dest = 'verbose',
                           action = 'store_true',
                           help = ('If specified, print more information than normal'))
    args = argparse.ArgumentParser(epilog = 'This program has context-sensitive help (e.g. try "... add --help")')
    subparsers = args.add_subparsers(help = 'Operation to perform',
                                     dest = 'operation')
    addargs = subparsers.add_parser('add',
                                    parents = [commonargs, optcommon],
                                    help = 'Add a user to the Murmur database')
    delargs = subparsers.add_parser('rm',
                                    parents = [commonargs, optcommon],
                                    help = 'Remove a user from the Murmur database')
    listargs = subparsers.add_parser('ls',
                                     parents = [optcommon],
                                     help = 'List users in the Murmur database')
    editargs = subparsers.add_parser('edit',
                                     parents = [commonargs, optcommon],
                                     help = 'Edit a user in the Murmur database')
    # Operation-specific optional arguments
    # Why did I even add this? It's not used *anywhere*.
    #addargs.add_argument('-n', '--name',
    #                     type = str,
    #                     metavar = '"Firstname Lastname"',
    #                     dest = 'name',
    #                     default = None,
    #                     help = 'The new user\'s (real) name')
    addargs.add_argument('-c', '--comment',
                         type = str,
                         metavar = '"This comment becomes the user\'s profile."',
                         dest = 'UserComment',
                         default = None,
                         help = 'The comment for the new user')
    addargs.add_argument('-e', '--email',
                         type = str,
                         metavar = 'email@domain.tld',
                         dest = 'UserEmail',
                         default = None,
                         help = 'The email address for the new user')
    addargs.add_argument('-C', '--certhash',
                         type = str,
                         metavar = 'CERTIFICATE_FINGERPRINT_HASH',
                         default = None,
                         dest = 'UserHash',
                         help = ('The certificate fingerprint hash. See gencerthash.py. ' +
                                 'This is the preferred way. ' +
                                 'If you do not specify this, you must specify -p/--passwordhash'))
    addargs.add_argument('-p', '--password',
                         type = str,
                         dest = 'UserPassword',
                         choices = ['stdin', 'prompt'],
                         default = None,
                         help = ('If not specified, you must specify -C/--certhash. Otherwise, either ' +
                                 '\'stdin\' (the password is being piped into this program) or \'prompt\' ' +
                                 '(a password will be asked for in a non-echoing prompt). "prompt" is much more secure and recommended.'))
    addargs.add_argument('-g', '--groups',
                         type = str,
                         metavar = 'CHANID:GROUP1(,CHANID:GROUP2,CHANID:GROUP3...)',
                         default = None,
                         help = ('A comma-separated list of groups the user should be added to. If a group ' +
                                 'doesn\'t exist, it will be created. CHANID is a ' +
                                 'numerical ID of the channel to assign the group to. ' +
                                 '(You can get channel IDs by doing "... ls -gv".) ' +
                                 'If no CHANID is provided, the root channel (0) will be used.'))
    # Listing should only take the DB as the "common" arg
    listargs.add_argument('-g', '--groups',
                          action = 'store_true',
                          dest = 'groups',
                          help = 'If specified, list groups (and their members), not users')
    listargs.add_argument('-s', '--server',
                          type = str,
                          dest = 'server',
                          default = None,
                          help = 'The server ID. Defaults to all servers. Specify one by the numerical ID.')
    # Deleting args
    delargs.add_argument('-n', '--no-prune',
                         dest = 'noprune',
                         action = 'store_true',
                         help = ('If specified, do NOT remove the ACLs and user info for the user as well (profile, ' +
                                 'certificate fingerprint, etc.)'))
    delargs.add_argument('-P', '--prune-groups',
                         dest = 'prunegrps',
                         action = 'store_true',
                         help = ('If specified, remove any groups the user was in ' +
                                 'that are now empty (i.e. the user was the only member)'))
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    if not args['operation']:
        #raise RuntimeError('You must specify an operation to perform. Try running with -h/--help.')
        exit('You must specify an operation to perform. Try running with -h/--help.')
    args['interactive'] = True
    mgmt = IceMgr(args)
    if args['operation'] == 'add':
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
