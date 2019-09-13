#!/usr/bin/env python3

import re

sudo_cmds = []

# All of these commands...
cmds = ['/usr/bin/extra-x86_64-build',
        '/usr/bin/testing-x86_64-build',
        '/usr/bin/staging-x86_64-build',
        '/usr/bin/multilib-build',
        '/usr/bin/multilib-testing-build',
        '/usr/bin/multilib-staging-build',
        '/usr/bin/makechrootpkg']

# Should allow all of these args.
args = ['-c',
        '-c -- -- --skippgpcheck --syncdeps --noconfirm --log --holdver --skipinteg',
        '-- -- --skippgpcheck --syncdeps --noconfirm --log --holdver --skipinteg']

for c in cmds:
    for a in args:
        sudo_cmds.append('{0} {1}'.format(c, a))

s = ''

s += 'Cmnd_Alias\tPKGBUILDER = \\\n'
for c in sudo_cmds:
    s += '\t\t\t\t{0}, \\\n'.format(c)

s = re.sub(r', \\s*$', '', s)
print(s)

