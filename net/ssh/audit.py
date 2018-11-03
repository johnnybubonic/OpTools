#!/usr/bin/env python3

import argparse
import paramiko
import socket


class SSHAuthInfo(object):
    def __init__(self, target, port = 22, banner = True, ciphers = True, digests = True, kex = True, key_types = True,
                 methods = True, hostkeys = True, version = True):
        self.target = target
        self.port = int(port)
        self.info = {'target': self.target,
                     'port': self.port,
                     'banner': banner,
                     'ciphers': ciphers,
                     'digests': digests,
                     'kex': kex,
                     'key_types': key_types,
                     'methods': methods,
                     'hostkeys': hostkeys,
                     'version': version}
        self._ssh = None
        if any((ciphers, banner, methods, digests, kex, key_types)):  # These need an SSH connection.
            self._ssh_dummy()
        if banner:
            self.getBanner()
        if hostkeys:
            self.getHostkeys()
        if version:
            self.getVersion()
        self._close()

    def _ssh_dummy(self):
        self._ssh = paramiko.Transport((self.target, self.port))
        self._ssh.connect()
        try:
            self._ssh.auth_none('')
        except paramiko.ssh_exception.BadAuthenticationType as err:
            secopts = self._ssh.get_security_options()
            if self.info['methods']:
                # https://stackoverflow.com/a/1257769
                self.info['methods'] = err.allowed_types
            if self.info['ciphers']:
                self.info['ciphers'] = list(secopts.ciphers)
            if self.info['digests']:
                self.info['digests'] = list(secopts.digests)
            if self.info['kex']:
                self.info['kex'] = list(secopts.kex)
            if self.info['key_types']:
                self.info['key_types'] = list(secopts.key_types)
        return()

    def getBanner(self):
        self.info['banner'] = None
        # https://github.com/paramiko/paramiko/issues/273#issuecomment-225058645 doesn't seem to work.
        # But https://github.com/paramiko/paramiko/pull/58#issuecomment-63857078 did!
        self.info['banner'] = self._ssh.get_banner()
        return()

    def getHostkeys(self):
        # TODO: how the hell do I get *all* hostkeys served?
        self.info['hostkeys'] = {}
        k = self._ssh.get_remote_server_key()
        self.info['hostkeys'][k.get_name()] = k.get_base64()
        return()

    def getVersion(self):
        self.info['version'] = None
        s = socket.socket()
        s.connect((self.target, self.port))
        try:
            # 8192 bytes is kind of overkill considering most are probably going to be around 20 bytes or so.
            self.info['version'] = s.recv(8192)
        except Exception as e:
            pass
        return()

    def _close(self):
        if self._ssh:
            self._ssh.close()

def parseArgs():
    args = argparse.ArgumentParser()
    args.add_argument('-b', '--no-banner',
                      action = 'store_false',
                      dest = 'banner',
                      help = 'Do not gather the SSH banner')
    args.add_argument('-c', '--no-ciphers',
                      action = 'store_false',
                      dest = 'ciphers',
                      help = 'Do not gather supported ciphers')
    args.add_argument('-d', '--no-digests',
                      action = 'store_false',
                      dest = 'digests',
                      help = 'Do not gather supported digests')
    args.add_argument('-m', '--no-methods',
                      action = 'store_false',
                      dest = 'methods',
                      help = 'Do not gather supported auth methods')
    args.add_argument('-k', '--no-hostkeys',
                      action = 'store_false',
                      dest = 'hostkeys',
                      help = 'Do not gather hostkeys')
    args.add_argument('-x', '--no-kex',
                      action = 'store_false',
                      dest = 'kex',
                      help = 'Do not gather supported key exchanges')
    args.add_argument('-t', '--no-key-types',
                      action = 'store_false',
                      dest = 'key_types',
                      help = 'Do not gather supported key types')
    args.add_argument('-v', '--no-version',
                      action = 'store_false',
                      dest = 'version',
                      help = 'Do not gather SSH version')
    args.add_argument('-p', '--port',
                      default = 22,
                      help = 'The port on target that the SSH daemon is running on. Default is 22')
    args.add_argument('target',
                      help = 'The server to run the check against')
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    i = SSHAuthInfo(**args)
    import pprint
    pprint.pprint(i.info)

if __name__ == '__main__':
    main()
