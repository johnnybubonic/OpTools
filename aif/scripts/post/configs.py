#!/usr/bin/env python3

import os
import pathlib
import pwd
import subprocess

def byobu(user = 'root'):
    homedir = os.path.expanduser('~{0}'.format(user))
    subprocess.run(['byobu-enable'])
    b = '{0}/.byobu'.format(homedir)
    # The keybindings, and general enabling
    confs = {'backend': 'BYOBU_BACKEND=tmux\n',
             'color': 'BACKGROUND=k\nFOREGROUND=w\nMONOCHROME=0',  # NOT a typo; the original source I got this from had no end newline.
             'color.tmux': 'BYOBU_DARK="\#333333"\nBYOBU_LIGHT="\#EEEEEE"\nBYOBU_ACCENT="\#75507B"\nBYOBU_HIGHLIGHT="\#DD4814"\n',
             'datetime.tmux': 'BYOBU_DATE="%Y-%m-%d "\nBYOBU_TIME="%H:%M:%S"\n',
             'keybindings': 'source $BYOBU_PREFIX/share/byobu/keybindings/common\n',
             'keybindings.tmux': 'unbind-key -n C-a\nset -g prefix ^A\nset -g prefix2 ^A\nbind a send-prefix\n',
             'profile': 'source $BYOBU_PREFIX/share/byobu/profiles/common\n',
             'profile.tmux': 'source $BYOBU_PREFIX/share/byobu/profiles/tmux\n',
             'prompt': '[ -r /usr/share/byobu/profiles/bashrc ] && . /usr/share/byobu/profiles/bashrc  #byobu-prompt#\n',
             '.screenrc': None,
             '.tmux.conf': None,
             '.welcome-displayed': None,
             'windows': None,
             'windows.tmux': None}
    for c in confs.keys():
        with open('{0}/{1}'.format(b, c), 'w') as f:
            if confs[c] is not None:
                f.write(confs[c])
            else:
                f.write('')
    # The status file- add some extras, and remove the session string which is broken apparently.
    # Holy shit I wish there was a way of storing compressed text in plaintext besides base64.
    statusconf = ["#    status - Byobu's default status enabled/disabled settings\n", '#\n', '#      Override these in $BYOBU_CONFIG_DIR/status\n',
                  '#      where BYOBU_CONFIG_DIR is XDG_CONFIG_HOME if defined,\n', '#      and $HOME/.byobu otherwise.\n', '#\n',
                  '#    Copyright (C) 2009-2011 Canonical Ltd.\n', '#\n', '#    Authors: Dustin Kirkland <kirkland@byobu.org>\n', '#\n',
                  '#    This program is free software: you can redistribute it and/or modify\n', '#    it under the terms of the GNU ' +
                  'General Public License as published by\n', '#    the Free Software Foundation, version 3 of the License.\n', '#\n',
                  '#    This program is distributed in the hope that it will be useful,\n', '#    but WITHOUT ANY WARRANTY; without even the ' +
                  'implied warranty of\n', '#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n', '#    GNU General Public License ' +
                  'for more details.\n', '#\n', '#    You should have received a copy of the GNU General Public License\n', '#    along with this ' +
                  'program.  If not, see <http://www.gnu.org/licenses/>.\n', '\n', "# Status beginning with '#' are disabled.\n", '\n', '# Screen has ' +
                  'two status lines, with 4 quadrants for status\n', 'screen_upper_left="color"\n', 'screen_upper_right="color whoami hostname ' +
                  'ip_address menu"\n', 'screen_lower_left="color logo distro release #arch session"\n', 'screen_lower_right="color network #disk_io ' +
                  'custom #entropy raid reboot_required updates_available #apport #services #mail users uptime #ec2_cost #rcs_cost #fan_speed #cpu_temp ' +
                  'battery wifi_quality #processes load_average cpu_count cpu_freq memory #swap disk #time_utc date time"\n', '\n', '# Tmux has one ' +
                  'status line, with 2 halves for status\n', 'tmux_left=" logo #distro release arch #session"\n', '# You can have as many tmux right ' +
                  'lines below here, and cycle through them using Shift-F5\n', 'tmux_right=" network disk_io #custom #entropy raid reboot_required ' +
                  '#updates_available #apport services #mail #users uptime #ec2_cost #rcs_cost #fan_speed #cpu_temp #battery #wifi_quality processes ' +
                  'load_average cpu_count cpu_freq memory #swap disk whoami hostname ip_address time_utc date time"\n', '#tmux_right="network ' +
                  '#disk_io #custom entropy raid reboot_required updates_available #apport #services #mail users uptime #ec2_cost #rcs_cost fan_speed ' +
                  'cpu_temp battery wifi_quality #processes load_average cpu_count cpu_freq memory #swap #disk whoami hostname ip_address #time_utc ' +
                  'date time"\n', '#tmux_right="network #disk_io custom #entropy raid reboot_required updates_available #apport #services #mail users ' +
                  'uptime #ec2_cost #rcs_cost #fan_speed #cpu_temp battery wifi_quality #processes load_average cpu_count cpu_freq memory #swap #disk ' +
                  '#whoami #hostname ip_address #time_utc date time"\n', '#tmux_right="#network disk_io #custom entropy #raid #reboot_required ' +
                  '#updates_available #apport #services #mail #users #uptime #ec2_cost #rcs_cost fan_speed cpu_temp #battery #wifi_quality #processes ' +
                  '#load_average #cpu_count #cpu_freq #memory #swap whoami hostname ip_address #time_utc disk date time"\n']
    with open('{0}/status'.format(b), 'w') as f:
        f.write(''.join(statusconf))
    # The statusrc file is another lengthy one.
    statusrc = ["#    statusrc - Byobu's default status configurations\n", '#\n', '#      Override these in $BYOBU_CONFIG_DIR/statusrc\n',
                '#      where BYOBU_CONFIG_DIR is XDG_CONFIG_HOME if defined,\n', '#      and $HOME/.byobu otherwise.\n', '#\n', '#    Copyright (C) ' +
                '2009-2011 Canonical Ltd.\n', '#\n', '#    Authors: Dustin Kirkland <kirkland@byobu.org>\n', '#\n', '#    This program is free software: ' +
                'you can redistribute it and/or modify\n', '#    it under the terms of the GNU General Public License as published by\n',
                '#    the Free Software Foundation, version 3 of the License.\n', '#\n', '#    This program is distributed in the hope that it will be ' +
                'useful,\n', '#    but WITHOUT ANY WARRANTY; without even the implied warranty of\n', '#    MERCHANTABILITY or FITNESS FOR A PARTICULAR ' +
                'PURPOSE.  See the\n', '#    GNU General Public License for more details.\n', '#\n', '#    You should have received a copy of the GNU ' +
                'General Public License\n', '#    along with this program.  If not, see <http://www.gnu.org/licenses/>.\n', '\n', '# Configurations that ' +
                'you can override; if you leave these commented out,\n', '# Byobu will try to auto-detect them.\n', '\n', '# This should be auto-detected ' +
                'for most distro, but setting it here will save\n', '# some call to lsb_release and the like.\n', '#BYOBU_DISTRO=Ubuntu\n', '\n',
                '# Default: depends on the distro (which is either auto-detected, either set\n', '# via $DISTRO)\n', '#LOGO="\\o/"\n', '\n', '# Abbreviate ' +
                'the release to N characters\n', '# By default, this is disabled.  But if you set RELEASE_ABBREVIATED=1\n', '# and your lsb_release is ' +
                '"precise", only "p" will be displayed\n', '#RELEASE_ABBREVIATED=1\n', '\n', '# Default: /\n', '#MONITORED_DISK=/\n', '\n', '# Minimum ' +
                'disk throughput that triggers the notification (in kB/s)\n', '# Default: 50\n', '#DISK_IO_THRESHOLD=50\n', '\n', '# Default: eth0\n',
                '#MONITORED_NETWORK=eth0\n', '\n', '# Unit used for network throughput (either bits per second or bytes per second)\n', '# Default: ' +
                'bits\n', '#NETWORK_UNITS=bytes\n', '\n', '# Minimum network throughput that triggers the notification (in kbit/s)\n', '# Default: 20\n',
                '#NETWORK_THRESHOLD=20\n', '\n', '# You can add an additional source of temperature here\n', '#MONITORED_TEMP=/proc/acpi/thermal_zone/' +
                'THM0/temperature\n', '\n', '# Default: C\n', '#TEMP=F\n', '\n', '#SERVICES="eucalyptus-nc|NC eucalyptus-cloud|CLC eucalyptus-walrus ' +
                'eucalyptus-cc|CC eucalyptus-sc|SC"\n', '\n', '#FAN=$(find /sys -type f -name fan1_input | head -n1)\n', '\n', '# You can set this to 1 ' +
                'to report your external/public ip address\n', '# Default: 0\n', '#IP_EXTERNAL=0\n', '\n', '# The users notification normally counts ssh ' +
                "sessions; set this configuration to '1'\n", '# to instead count number of distinct users logged onto the system\n', '# Default: 0\n',
                '#USERS_DISTINCT=0\n', '\n', '# Set this to zero to hide seconds int the time display\n', '# Default 1\n', '#TIME_SECONDS=0\n']
    with open('{0}/statusrc'.format(b), 'w') as f:
        f.write(''.join(statusrc))
    setPerms(user, b)
    return()

def vim():
    vimc = ['\n', 'set nocompatible\n', 'set number\n', 'syntax on\n', 'set paste\n', 'set ruler\n', 'if has("autocmd")\n','  au BufReadPost * if ' +
            'line("\'\\"") > 1 && line("\'\\"") <= line("$") | exe "normal! g\'\\"" | endif\n', 'endif\n', '\n', '" bind F3 to insert a timestamp.\n', '" In ' +
            'normal mode, insert.\n', 'nmap <F3> i<C-R>=strftime("%c")<CR><Esc>\n', '\n', 'set pastetoggle=<F2>\n', '\n', '" https://stackoverflow.com/' +
            'questions/27771616/turn-off-all-automatic-code-complete-in-jedi-vim\n', 'let g:jedi#completions_enabled = 0\n', 'let g:jedi#show_call_' +
            'signatures = "0"\n']
    with open('/etc/vimrc', 'a') as f:
        f.write(''.join(vimc))
    setPerms('root', '/etc/vimrc')
    return()

def bash():
    bashc = ['\n', 'alias vi=/usr/bin/vim\n', 'export EDITOR=vim\n', '\n', 'if [ -f ~/.bashrc ];\n', 'then\n', ' source ~/.bashrc\n', 'fi \n',
             'if [ -d ~/bin ];\n', 'then\n', ' export PATH="$PATH:~/bin"\n', 'fi\n', '\n', 'alias grep="grep --color"\n',
             'alias egrep="egrep --color"\n', '\n', 'alias ls="ls --color=auto"\n', 'alias vi="/usr/bin/vim"\n', '\n', 'export HISTTIMEFORMAT="%F %T "\n',
             'export PATH="${PATH}:/sbin:/bin:/usr/sbin"\n']
    with open('/etc/bash.bashrc', 'a') as f:
        f.write(''.join(bashc))
    setPerms('root', '/etc/bash.bashrc')
    return()

def mlocate():
    subprocess.run(['updatedb'])
    return()

def setPerms(user, path):
    uid = pwd.getpwnam(user).pw_uid
    gid = pwd.getpwnam(user).pw_gid
    pl = pathlib.PurePath(path).parts
    for basedir, dirs, files in os.walk(path):
        os.chown(basedir, uid, gid)
        if os.path.isdir(basedir):
            os.chmod(basedir, 0o755)
        elif os.path.isfile(basedir):
            os.chmod(basedir, 0o644)
        for f in files:
            os.chown(os.path.join(basedir, f), uid, gid)
            os.chmod(os.path.join(basedir, f), 0o644)
    return()

def main():
    byobu()
    vim()
    bash()
    mlocate()

if __name__ == '__main__':
    main()
