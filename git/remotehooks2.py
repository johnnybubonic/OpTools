#!/usr/bin/env python3

import json
import os
import re
import sys
# Can we use paramiko for remotecmds?
try:
    import paramiko
    import socket
    has_ssh = True
except ImportError:
    has_ssh = False
# Can we use the python git module?
try:
    import git  # "python-gitpython" in Arch; https://github.com/gitpython-developers/gitpython
    has_git = True
except ImportError:
    has_git = False


class repoHooks(object):
    def __init__(self):
        with open(os.path.join(os.environ['HOME'],
                               '.gitolite',
                               'local',
                               'hooks',
                               'repo-specific',
                               'githooks.json'), 'r') as f:
            self.cfg = json.loads(f.read())
        self.repos = list(self.cfg.keys())
        self.env = os.environ.copy()
        if 'GIT_DIR' in self.env.keys():
            del(self.env['GIT_DIR'])
        self.repo = self.env['GL_REPO']

    def remoteExec(self):
        for _host in self.repos[self.repo]['remotecmds'].keys():
            if len(_host.split(':')) == 2:
                _server, _port = [i.strip() for i in _host.split(':')]
            else:
                _port = 22
                _server = _host.split(':')[0]
            _h = self.repos[self.repo]['remotecmds'][_host]
            for _user in _h.keys():
                _u = _h[_user]
                if has_ssh:
                    _ssh = paramiko.SSHClient()
                    _ssh.load_system_host_keys()
                    _ssh.missing_host_key_policy(paramiko.AutoAddPolicy())
                    _ssh.connect(_server,
                                 int(_port),
                                 _user)
                    for _cmd in _h.keys():
                        pass  # DO STUFF HERE
                else:
                    return()  # no-op; no paramiko

    def localExec(self):
        pass

def main():
    h = repoHooks()
    if h.repo not in h.repos:
        return()


if __name__ == '__main__':
    main()
