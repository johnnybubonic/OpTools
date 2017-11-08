#!/usr/bin/env python3

import argparse
import grp
import os
import pwd
import re
import subprocess
import sys

# Defaults
#def_supported_keys = subprocess.run(['ssh',
#                                     '-Q',
#                                     'key'], stdout = subprocess.PIPE).stdout.decode('utf-8').splitlines()
def_supported_keys = ['dsa', 'ecdsa', 'ed25519', 'rsa']
def_mode = 'append'
def_syshostkeys = '/etc/ssh/ssh_known_hosts'
def_user = pwd.getpwuid(os.geteuid())[0]
def_grp = grp.getgrgid(os.getegid())[0]


class hostscanner(object):
    def __init__(self, args):
        self.args = args
        if self.args['keytypes'] == ['all']:
            self.args['keytypes'] = def_supported_keys
        if self.args['system']:
            if os.geteuid() != 0:
                exit(('You have specified system-wide modification but ' +
                      'are not running with root privileges! Exiting.'))
            self.args['output'] = def_syshostkeys
        if self.args['output'] != sys.stdout:
            _pardir = os.path.dirname(os.path.abspath(os.path.expanduser(self.args['output'])))
            if _pardir.startswith('/home'):
                _octmode = 0o700
            else:
                _octmode = 0o755
            os.makedirs(_pardir, mode = _octmode, exist_ok = True)
            os.chown(_pardir,
                     pwd.getpwnam(self.args['chown_user'])[2],
                     grp.getgrnam(self.args['chown_grp'])[2])

    def getHosts(self):
        self.keys = {}
        _hosts = os.path.abspath(os.path.expanduser(self.args['infile']))
        with open(_hosts, 'r') as f:
            for l in f.readlines():
                l = l.strip()
                if re.search('^\s*(#.*)?$', l, re.MULTILINE):
                    continue  # Skip commented and blank lines
                k = re.sub('^([0-9a-z-\.]+)\s*#.*$',
                           '\g<1>',
                           l.strip().lower(),
                           re.MULTILINE)
                self.keys[k] = []
        return()

    def getKeys(self):
        def parseType(k):
            _newkey = re.sub('^ssh-', '', k).split('-')[0]
            if _newkey == 'dss':
                _newkey = 'dsa'
            return(_newkey)
        for h in list(self.keys.keys()):
            _h = h.split(':')
            if len(_h) == 1:
                _host = _h[0]
                _port = 22
            elif len(_h) == 2:
                _host = _h[0]
                _port = int(_h[1])
            _cmdline = ['ssh-keyscan',
                        '-t', ','.join(self.args['keytypes']),
                        '-p', str(_port),
                        _host]
            if self.args['hash']:
                #https://security.stackexchange.com/a/56283
                # verify via:
                # SAMPLE ENTRY: |1|F1E1KeoE/eEWhi10WpGv4OdiO6Y=|3988QV0VE8wmZL7suNrYQLITLCg= ssh-rsa ...
                #key=$(echo F1E1KeoE/eEWhi10WpGv4OdiO6Y= | base64 -d | xxd -p)
                #echo -n "192.168.1.61" | openssl sha1 -mac HMAC -macopt hexkey:${key} | awk '{print $2}' | xxd -r -p | base64
                _cmdline.insert(1, '-H')
            _cmd = subprocess.run(_cmdline,
                                  stdout = subprocess.PIPE,
                                  stderr = subprocess.PIPE)
            if not re.match('\s*#.*', _cmd.stderr.decode('utf-8')):
                _printerr = []
                for i in _cmd.stderr.decode('utf-8').splitlines():
                    if i.strip() not in _printerr:
                        _printerr.append(i.strip())
                print('{0}: errors detected; skipping ({1})'.format(h, '\n'.join(_printerr)))
                del(self.keys[h])
                continue
            for l in _cmd.stdout.decode('utf-8').splitlines():
                _l = l.split()
                _key = {'type': _l[1],
                        'host': _l[0],
                        'key': _l[2]}
                if parseType(_key['type']) in self.args['keytypes']:
                    self.keys[h].append(_key)
        return()

    def write(self):
        for h in self.keys.keys():
            for i in self.keys[h]:
                _s = '# Automatically added via hostscan.py\n{0} {1} {2}\n'.format(i['host'],
                                                                                   i['type'],
                                                                                   i['key'])
                if self.args['output'] == sys.stdout:
                    print(_s, end = '')
                else:
                    if self.args['writemode'] == 'append':
                        _wm = 'a'
                    else:
                        _wm = 'w'
                    with open(self.args['output'], _wm) as f:
                                f.write(_s)
                    os.chmod(self.args['output'], 0o644)
                    os.chown(self.args['output'],
                             pwd.getpwnam(self.args['chown_user'])[2],
                             grp.getgrnam(self.args['chown_grp'])[2])
        return()

def parseArgs():
    def getTypes(t):
        keytypes = t.split(',')
        keytypes = [k.strip() for k in keytypes]
        for k in keytypes:
            if k not in ('all', *def_supported_keys):
                raise argparse.ArgumentError('Must be one or more of the following: all, {0}'.format(', '.join(def_supported_keys)))
        return(keytypes)
    args = argparse.ArgumentParser(description = ('Scan a list of hosts and present their hostkeys in ' +
                                                  'a format suitable for an SSH known_hosts file.'))
    args.add_argument('-u',
                      '--user',
                      dest = 'chown_user',
                      default = def_user,
                      help = ('The username to chown the file to (if \033[1m{0}\033[0m is specified). ' +
                              'Default: \033[1m{1}\033[0m').format('-o/--output', def_user))
    args.add_argument('-g',
                      '--group',
                      dest = 'chown_grp',
                      default = def_grp,
                      help = ('The group to chown the file to (if \033[1m{0}\033[0m is specified). ' +
                              'Default: \033[1m{1}\033[0m').format('-o/--output', def_grp))
    args.add_argument('-H',
                      '--hash',
                      dest = 'hash',
                      action = 'store_true',
                      help = ('If specified, hash the hostkeys (see ssh-keyscan(1)\'s -H option for more info)'))
    args.add_argument('-m',
                      '--mode',
                      dest = 'writemode',
                      default = def_mode,
                      choices = ['append', 'replace'],
                      help = ('If \033[1m{0}\033[0m is specified, the mode to use for the ' +
                              'destination file. The default is \033[1m{1}\033[0m').format('-o/--output', def_mode))
    args.add_argument('-k',
                      '--keytypes',
                      dest = 'keytypes',
                      type = getTypes,
                      default = 'all',
                      help = ('A comma-separated list of key types to add (if supported by the target host). ' +
                              'The default is to add all keys found. Must be one (or more) of: \033[1m{0}\033[0m').format(', '.join(def_supported_keys)))
    args.add_argument('-o',
                      '--output',
                      default = sys.stdout,
                      metavar = 'OUTFILE',
                      dest = 'output',
                      help = ('If specified, write the hostkeys to \033[1m{0}\033[0m instead of ' +
                              '\033[1m{1}\033[0m (the default). ' +
                              'Overrides \033[1m{2}\033[0m').format('OUTFILE',
                                                                    'stdout',
                                                                    '-S/--system-wide'))
    args.add_argument('-S',
                      '--system-wide',
                      dest = 'system',
                      action = 'store_true',
                      help = ('If specified, apply to the entire system (not just the ' +
                              'specified/running user) via {0}. ' +
                              'Requires \033[1m{1}\033[0m in /etc/ssh/ssh_config (usually ' +
                              'enabled silently by default) and running with root ' +
                              'privileges').format(def_syshostkeys,
                                                   'GlobalKnownHostsFile {0}'.format(def_syshostkeys)))
    args.add_argument(metavar = 'HOSTLIST_FILE',
                      dest = 'infile',
                      help = ('The path to the list of hosts. Can contain blank lines and/or comments. ' +
                              'One host per line. Can be \033[1m{0}\033[0m (as long as it\'s resolvable), ' +
                              '\033[1m{1}\033[0m, or \033[1m{2}\033[0m. To specify an alternate port, ' +
                              'add \033[1m{3}\033[0m to the end (e.g. ' +
                              '"some.host.tld:22")').format('hostname',
                                                            'IP address',
                                                            'FQDN',
                                                            ':<PORTNUM>'))
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    scan = hostscanner(args)
    scan.getHosts()
    scan.getKeys()
    scan.write()

if __name__ == '__main__':
    main()
