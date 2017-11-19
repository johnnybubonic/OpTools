#!/usr/bin/env python3

import ast  # Needed for localhost cmd strings
import json
import os
import re
import sys
modules = {}
try:
    import git
    modules['git'] = True
except ImportError:
    import subprocess
    modules['git'] = False
try:
    import paramiko
    import socket
    modules['ssh'] = True
except ImportError:
    modules['ssh'] = False



repos = {}
repos['bdisk'] = {'remotecmds': {'g.rainwreck.com': {'gitbot': {'cmds': ['git -C /var/lib/gitbot/clonerepos/BDisk pull',
                                                                         'git -C /var/lib/gitbot/clonerepos/BDisk pull --tags',
                                                                         'asciidoctor /var/lib/gitbot/clonerepos/BDisk/docs/manual/HEAD.adoc -o /srv/http/bdisk/index.html']}}}}
repos['test'] = {'remotecmds': {'g.rainwreck.com': {'gitbot': {'cmds': ['echo $USER']}}}}
repos['games-site'] = {'remotecmds': {'games.square-r00t.net':
                                    {'gitbot':
                                        {'cmds': ['cd /srv/http/games-site && git pull']}}}}
repos['aif-ng'] = {'cmds': [['asciidoctor', '/opt/git/repo.checkouts/aif-ng/docs/README.adoc', '-o', '/srv/http/aif/index.html']]}

def execHook(gitinfo = False):
    if not gitinfo:
        gitinfo = getGitInfo()
    repo = gitinfo['repo'].lower()
    print('Executing hooks for {0}:{1}...'.format(repo, gitinfo['branch']))
    print('This commit: {0}\nLast commit: {1}'.format(gitinfo['currev'], gitinfo['oldrev']))
    # Execute local commands first
    if 'cmds' in repos[repo].keys():
        for cmd in repos[repo]['cmds']:
            print('\tExecuting {0}...'.format(' '.join(cmd)))
            subprocess.call(cmd)
    if 'remotecmds' in repos[repo].keys():
        for host in repos[repo]['remotecmds'].keys():
            if 'port' in repos[repo]['remotecmds'][host].keys():
                port = int(repos[repo]['remotecmds'][host]['port'])
            else:
                port = 22
            for user in repos[repo]['remotecmds'][host].keys():
                print('{0}@{1}:'.format(user, host))
                if paramikomodule:
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(host, username = user, port = port)
                    try:
                        for cmd in repos[repo]['remotecmds'][host][user]['cmds']:
                            print('\tExecuting \'{0}\'...'.format(cmd))
                            stdin, stdout, stderr = ssh.exec_command(cmd)
                            stdout = stdout.read().decode('utf-8')
                            stderr = stderr.read().decode('utf-8')
                            print(stdout)
                            if stderr != '':
                                print(stderr)
                    except paramiko.AuthenticationException:
                        print('({0}@{1}) AUTHENTICATION FAILED!'.format(user, host))
                    except paramiko.BadHostKeyException:
                        print('({0}@{1}) INCORRECT HOSTKEY!'.format(user, host))
                    except paramiko.SSHException:
                        print('({0}@{1}) FAILED TO ESTABLISH SSH!'.format(user, host))
                    except socket.error:
                        print('({0}@{1}) SOCKET CONNECTION FAILURE! (DNS, timeout/firewall, etc.)'.format(user, host))
                else:
                    for cmd in repos[repo]['remotecmds'][host][user]['cmds']:
                        try:
                            print('\tExecuting \'{0}\'...'.format(cmd))
                            subprocess.call(['ssh', '{0}@{1}'.format(user, host), cmd])
                        except:
                            print('({0}@{1}) An error occurred!'.format(user, host))

def getGitInfo():
    refs = sys.argv[1].split('/')
    gitinfo = {}
    if refs[1] == 'tags':
        gitinfo['branch'] = False
        gitinfo['tag'] = refs[2]
    elif refs[1] == 'heads':
        gitinfo['branch'] = refs[2]
        gitinfo['tag'] = False
    gitinfo['repo'] = os.environ['GL_REPO']
    gitinfo['user'] = os.environ['GL_USER']
    clientinfo = os.environ['SSH_CONNECTION'].split()
    gitinfo['ssh'] = {'client': {'ip': clientinfo[0], 'port': clientinfo[1]},
                      'server': {'ip': clientinfo[2], 'port': clientinfo[3]},
                      'user': os.environ['USER']
                     }
    if os.environ['GIT_DIR'] == '.':
        gitinfo['dir'] = os.environ['PWD']
    else:
        #gitinfo['dir'] = os.path.join(os.environ['GL_REPO_BASE'], gitinfo['repo'], '.git')
        gitinfo['dir'] = os.path.abspath(os.path.expanduser(os.environ['GIT_DIR']))
    if gitmodule:
        # This is preferred, because it's a lot more faster and a lot more flexible.
        #https://gitpython.readthedocs.io/en/stable
        gitobj = git.Repo(gitinfo['dir'])
        commits = list(gitobj.iter_commits(gitobj.head.ref.name, max_count = 2))
    else:
        commits = subprocess.check_output(['git', 'rev-parse', 'HEAD..HEAD^1']).decode('utf-8').splitlines()
    gitinfo['oldrev'] = re.sub('^\^', '', commits[1])
    gitinfo['currev'] = re.sub('^\^', '', commits[0])
    return(gitinfo)
    #sys.exit(0)

def main():
    execHook()

if __name__ == '__main__':
    main()
