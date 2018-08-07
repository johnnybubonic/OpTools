#!/usr/bin/env python3

# Pythonized automated way of running https://sysadministrivia.com/news/hardening-ssh-security
# TODO: check for cryptography module. if it exists, we can do this entirely pythonically
#       without ever needing to use subprocess/ssh-keygen, i think!

import datetime
import glob
import os
import pwd
import re
import shutil
import subprocess

conf_options = {}
conf_options['sshd'] = {'KexAlgorithms': 'curve25519-sha256@libssh.org,diffie-hellman-group-exchange-sha256',
                        'Protocol': '2',
                        'HostKey': ['/etc/ssh/ssh_host_ed25519_key',
                                    '/etc/ssh/ssh_host_rsa_key'],
                        'PermitRootLogin': 'prohibit-password',
                        'PasswordAuthentication': 'no',
                        'ChallengeResponseAuthentication': 'no',
                        'PubkeyAuthentication': 'yes',
                        'Ciphers': 'chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com,aes256-ctr,aes192-ctr,aes128-ctr',
                        'MACs': ('hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,umac-128-etm@openssh.com,' +
                                 'hmac-sha2-512,hmac-sha2-256,umac-128@openssh.com')}
# Uncomment if this is further configured
#conf_options['sshd']['AllowGroups'] = 'ssh-user'

conf_options['ssh'] = {'Host': {'*': {'KexAlgorithms': 'curve25519-sha256@libssh.org,diffie-hellman-group-exchange-sha256',
                                      'PubkeyAuthentication': 'yes',
                                      'HostKeyAlgorithms': 'ssh-ed25519-cert-v01@openssh.com,ssh-rsa-cert-v01@openssh.com,ssh-ed25519,ssh-rsa'}}}
# Uncomment below if Github still needs diffie-hellman-group-exchange-sha1 sometimes.
#conf_options['ssh']['Host']['github.com'] = {'KexAlgorithms': 'curve25519-sha256@libssh.org,diffie-hellman-group-exchange-sha256,' +
#                                             'diffie-hellman-group-exchange-sha1,diffie-hellman-group14-sha1'}


def hostKeys(buildmoduli):
    # Starting haveged should help lessen the time load, but not much.
    if os.path.lexists('/usr/bin/haveged'):
        # We could use psutil here, but then that's a python dependency we don't need.
        # We could parse the /proc directory, but that's quite unnecessary. pgrep's installed by default on Arch.
        with open(os.devnull, 'wb') as devnull:
            if subprocess.run(['pgrep', 'haveged'], stdout = devnull).returncode != 0:
                subprocess.run(['haveged'], stdout = devnull)
    #Warning: The moduli stuff takes a LONG time to run. Hours.
    if buildmoduli:
        subprocess.run(['ssh-keygen', '-G', '/etc/ssh/moduli.all', '-b', '4096', '-q'])
        subprocess.run(['ssh-keygen', '-T', '/etc/ssh/moduli.safe', '-f', '/etc/ssh/moduli.all', '-q'])
        if os.path.lexists('/etc/ssh/moduli'):
            os.rename('/etc/ssh/moduli', '/etc/ssh/moduli.old')
        os.rename('/etc/ssh/moduli.safe', '/etc/ssh/moduli')
        os.remove('/etc/ssh/moduli.all')
    for suffix in ('', '.pub'):
        for k in glob.glob('/etc/ssh/ssh_host_*key{0}'.format(suffix)):
            os.rename(k, '{0}.old.{1}'.format(k, int(datetime.datetime.utcnow().timestamp())))
    subprocess.run(['ssh-keygen', '-t', 'ed25519', '-f', '/etc/ssh/ssh_host_ed25519_key', '-q', '-N', ''])
    subprocess.run(['ssh-keygen', '-t', 'rsa', '-b', '4096', '-f', '/etc/ssh/ssh_host_rsa_key', '-q', '-N', ''])
    # We currently don't use this, but for simplicity's sake let's return the host keys.
    hostkeys = {}
    for k in ('ed25519', 'rsa'):
        with open('/etc/ssh/ssh_host_{0}_key.pub'.format(k), 'r') as f:
            hostkeys[k] = f.read()
    return(hostkeys)

def config(opts, t):
    special = {'sshd': {}, 'ssh': {}}
    # We need to handle these directives a little differently...
    special['sshd']['opts'] = ['Match']
    special['sshd']['filters'] = ['User', 'Group', 'Host', 'LocalAddress', 'LocalPort', 'Address']
    # These are arguments supported by each of the special options. We'll use this to verify entries.
    special['sshd']['args'] = ['AcceptEnv', 'AllowAgentForwarding', 'AllowGroups', 'AllowStreamLocalForwarding', 'AllowTcpForwarding',
                               'AllowUsers', 'AuthenticationMethods', 'AuthorizedKeysCommand', 'AuthorizedKeysCommandUser',
                               'AuthorizedKeysFile', 'AuthorizedPrincipalsCommand', 'AuthorizedPrincipalsCommandUser', 'AuthorizedPrincipalsFile',
                               'Banner', 'ChrootDirectory', 'ClientAliveCountMax', 'ClientAliveInterval', 'DenyGroups', 'DenyUsers', 'ForceCommand',
                               'GatewayPorts', 'GSSAPIAuthentication', 'HostbasedAcceptedKeyTypes', 'HostbasedAuthentication',
                               'HostbasedUsesNameFromPacketOnly', 'IPQoS', 'KbdInteractiveAuthentication', 'KerberosAuthentication', 'MaxAuthTries',
                               'MaxSessions', 'PasswordAuthentication', 'PermitEmptyPasswords', 'PermitOpen', 'PermitRootLogin', 'PermitTTY',
                               'PermitTunnel', 'PermitUserRC', 'PubkeyAcceptedKeyTypes', 'PubkeyAuthentication', 'RekeyLimit', 'RevokedKeys',
                               'StreamLocalBindMask', 'StreamLocalBindUnlink', 'TrustedUserCAKeys', 'X11DisplayOffset', 'X11Forwarding', 'X11UseLocalHost']
    special['ssh']['opts'] = ['Host', 'Match']
    special['ssh']['args'] = ['canonical', 'exec', 'host', 'originalhost', 'user', 'localuser']
    cf = '/etc/ssh/{0}_config'.format(t)
    shutil.copy2(cf, '{0}.bak.{1}'.format(cf, int(datetime.datetime.utcnow().timestamp())))
    with open(cf, 'r') as f:
        conf = f.readlines()
    conf.append('\n\n# Added per https://sysadministrivia.com/news/hardening-ssh-security\n\n')
    confopts = []
    # Get an index of directives pre-existing in the config file.
    for line in conf[:]:
        opt = line.split()
        if opt:
            if not re.match('^(#.*|\s+.*)$', opt[0]):
                confopts.append(opt[0])
    #print(confopts)
    # We also need to modify the config file- comment out starting with the first occurrence of the 
    # specopts, if it exists. This is why we make a backup.
    commentidx = None
    for idx, i in enumerate(conf):
        if re.match('^({0})\s+.*$'.format('|'.join(special[t]['opts'])), i):
            commentidx = idx
            break
    if commentidx is not None:
        idx = commentidx
        while idx <= (len(conf) - 1):
            conf[idx] = '#{0}'.format(conf[idx])
            idx += 1
    # Now we actually start replacing/adding some major configuration.
    for o in opts.keys():
        if o in special[t]['opts'] or isinstance(opts[o], dict):
            # We need to put these at the bottom of the file due to how they're handled by sshd's config parsing.
            continue
        # We handle these a little specially too- they're for multiple lines sharing the same directive.
        # Since the config should be explicit, we remove any existing entries specified that we find.
        else:
            if o in confopts:
                #print('commenting out old {0}'.format(o))
                # If I was more worried about recursion, or if I was appending here, I should use conf[:].
                # But I'm not. So I won't.
                for idx, opt in enumerate(conf):
                    if re.match('^{0}(\s.*)?\n$'.format(o), opt):
                        #l = opt.split()
                        #conf[idx] = '#{0} {1}'.format(l[0].strip, l[1].strip)
                        #print('old {0}: {1}'.format(o, conf[idx]))
                        conf[idx] = '#{0}'.format(opt)
                        #print('new {0}: {1}'.format(o, conf[idx]))
            # Here we handle the "multiple-specifying" options- notably, HostKey.
            if isinstance(opts[o], list):
                for l in opts[o]:
                    if l is not None:
                        conf.append('{0} {1}\n'.format(o, l))
                    else:
                        conf.append('{0}\n'.format(o))
            else:
                # So it isn't something we explicitly save until the end (such as a Match or Host),
                # and it isn't something that's specified multiple times.
                if opts[o] is not None:
                    conf.append('{0} {1}\n'.format(o, opts[o]))
                else:
                    conf.append('{0}\n'.format(o))
    # NOW we can add the Host/Match/etc. directives.
    for o in opts.keys():
        if isinstance(opts[o], dict):
            for k in opts[o].keys():
                conf.append('{0} {1}\n'.format(o, k))
                for l in opts[o][k].keys():
                    if opts[o][k][l] is not None:
                        conf.append('\t{0} {1}\n'.format(l, opts[o][k][l]))
                    else:
                        conf.append('\t{0}\n'.format(l))
    with open(cf, 'w') as f:
        f.write(''.join(conf))
    return()

def clientKeys(user = 'root'):
    uid = pwd.getpwnam(user).pw_uid
    gid = pwd.getpwnam(user).pw_gid
    homedir = os.path.expanduser('~{0}'.format(user))
    sshdir = '{0}/.ssh'.format(homedir)
    os.makedirs(sshdir, mode = 0o700, exist_ok = True)
    if not os.path.lexists('{0}/id_ed25519'.format(sshdir)) and not os.path.lexists('{0}/id_ed25519.pub'.format(sshdir)):
        subprocess.run(['ssh-keygen', '-t', 'ed25519', '-o', '-a', '100',
                        '-f', '{0}/id_ed25519'.format(sshdir), '-q', '-N', ''])
    if not os.path.lexists('{0}/id_rsa'.format(sshdir)) and not os.path.lexists('{0}/id_rsa.pub'.format(sshdir)):
        subprocess.run(['ssh-keygen', '-t', 'rsa', '-b', '4096', '-o', '-a', '100',
                        '-f', '{0}/id_rsa'.format(sshdir), '-q', '-N', ''])
    for basedir, dirs, files in os.walk(sshdir):
        os.chown(basedir, uid, gid)
        os.chmod(basedir, 0o700)
        for f in files:
            os.chown(os.path.join(basedir, f), uid, gid)
            os.chmod(os.path.join(basedir, f), 0o600)
    if 'pubkeys' not in globals():
        pubkeys = {}
    pubkeys[user] = {}
    for k in ('ed25519', 'rsa'):
        with open('{0}/id_{1}.pub'.format(sshdir, k), 'r') as f:
            pubkeys[user][k] = f.read()
    return(pubkeys)
        
def main():
    _chkfile = '/etc/ssh/.aif-generated'
    if not os.path.isfile(_chkfile):
        #Warning: The moduli stuff takes a LONG time to run. Hours.
        buildmoduli = True
        hostKeys(buildmoduli)
    for t in ('sshd', 'ssh'):
        config(conf_options[t], t)
    clientKeys()
    with open(_chkfile, 'w') as f:
        f.write(('ssh, sshd, and hostkey configurations/keys have been ' +
                 'modified by sshsecure.py from OpTools.\nhttps://git.square-r00t.net/OpTools/\n'))
    return()

if __name__ == '__main__':
    main()
