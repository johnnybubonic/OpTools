#!/usr/bin/env python3

# Because:
#   - SSH timeout doesn't work with byobu/screen/tmux
#   - SSH timeout can be overridden client-side
#   - $TMOUT can be overridden user-side
# we need to actually kill the sshd process attached to the SSH session.

import datetime
import os
import psutil
import subprocess

# in seconds. 5 minutes = 300 seconds.
# if "auto", we'll try checking $TMOUT in the system bashrc and sshd_config, in that order.
timeout = 'auto'
# only apply to ssh connections instead of ssh + local.
# THIS WILL KILL SCREEN/TMUX CONNECTIONS. USE WITH CAUTION.
only_ssh = True
# send a closing message.
goodbye = True
# the message to send to the user if goodbye == True.
# can use the following for substitution:
#   pid          - The PID if the user's login process.
#   terminal     - The terminal they're logged in on.
#   loginlength  - How long they've been logged in (in minutes).
#   logintime    - When they logged in.
#   timeout      - The allowed length of time for inactivity until a timeout.
goodbye_mesg = ('You have been logged in for {loginlength} seconds (since {logintime}) on '
                '{terminal} ({pid}).\n'
                'However, as per security policy, you have exceeded the allowed idle timeout ({timeout}).\n'
                'As such, your session will now be terminated. Please feel free to reconnect.')
# exclude these usernames
exclude_users = []


# Get the SSHD PIDs.
ssh_pids = [p for p in psutil.process_iter() if p.name() == 'sshd']
# If the timeout is set to auto, try to find it.
if timeout == 'auto':
    import re
    #tmout_re = re.compile('^\s*#*(export\s*)?TMOUT=([0-9]+).*$')
    tmout_re = re.compile('^\s*(export\s*)?TMOUT=([0-9]+).*$')
    # We don't bother with factoring in ClientAliveCountMax.
    # sshd_re = re.compile('^\s*#*ClientAliveCountMax\s+([0-9+]).*$')
    sshd_re = re.compile('^\s*ClientAliveInterval\s+([0-9+]).*$')
    for f in ('/etc/bashrc', '/etc/bash.bashrc'):
        if not os.path.isfile(f):
            continue
        with open(f, 'r') as fh:
            conf = fh.read()
        for line in conf.splitlines():
            if tmout_re.search(line):
                try:
                    timeout = int(tmout_re.sub('\g<2>', line))
                    break
                except ValueError:
                    continue
    if not isinstance(timeout, int):  # keep going; check sshd_config
        with open('/etc/ssh/sshd_config', 'r') as f:
            conf = f.read()
        for line in conf.splitlines():
            if sshd_re.search(line):
                try:
                    timeout = int(tmout_re.sub('\g<1>', line))
                    break
                except ValueError:
                    continue
    # Finally, set a default. 5 minutes is sensible.
    timeout = 300


def get_idle(user):
    idle_time = None
    try:
        # https://unix.stackexchange.com/a/332704/284004
        last_used = datetime.datetime.fromtimestamp(os.stat('/dev/{0}'.format(user.terminal)).st_atime)
        idle_time = datetime.datetime.utcnow() - last_used
    except FileNotFoundError:
        # It's probably a graphical login (e.g. gnome uses ::1) - you're on your own.
        pass
    return(idle_time)


for user in psutil.users():
    if user.name in exclude_users:
        continue
    login_pid = user.pid
    login_length = (datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(user.started))
    if login_length.total_seconds() < timeout:
        continue  # they haven't even been logged in for long enough yet.
    idle_time = get_idle(user)
    try:
        diff = idle_time.total_seconds() >= timeout
    except AttributeError:
        # Something went wrong when getting idle_time. probably a graphical desktop login.
        diff = False
    if diff:
        fmt_vals = {'pid': user.pid,
                    'terminal': user.terminal,
                    'loginlength': login_length,
                    'logintime': datetime.datetime.fromtimestamp(user.started),
                    'timeout': timeout}
        fmtd_goodbye = goodbye_mesg.format(**fmt_vals)
        if only_ssh:
            if user.pid in ssh_pids:
                if goodbye:
                    subprocess.run(['write',
                                    user.name,
                                    user.terminal],
                                   input = fmtd_goodbye.encode('utf-8'))
                psutil.Process(user.pid).terminate()
        else:
            if goodbye:
                subprocess.run(['write',
                                user.name,
                                user.terminal],
                               input = fmtd_goodbye.encode('utf-8'))
            psutil.Process(user.pid).terminate()
