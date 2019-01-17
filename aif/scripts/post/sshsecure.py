#!/usr/bin/env python3

# Pythonized automated way of running https://sysadministrivia.com/news/hardening-ssh-security
# TODO: check for cryptography module. if it exists, we can do this entirely pythonically
#       without ever needing to use subprocess/ssh-keygen, i think!

# Thanks to https://stackoverflow.com/a/39126754.

# Also, I need to re-write this. It's getting uglier.

# stdlib
import datetime
import glob
import os
import pwd
import re
import signal
import shutil
import subprocess  # REMOVE WHEN SWITCHING TO PURE PYTHON
#### PREP FOR PURE PYTHON IMPLEMENTATION ####
# # non-stdlib - testing and automatic install if necessary.
# # TODO #
# - cryptography module won't generate new-format "openssh-key-v1" keys.
# - See https://github.com/pts/py_ssh_keygen_ed25519 for possible conversion to python 3
# - https://github.com/openssh/openssh-portable/blob/master/PROTOCOL.key
# - https://github.com/pyca/cryptography/issues/3509 and https://github.com/paramiko/paramiko/issues/1136
# has_crypto = False
# pure_py = False
# has_pip = False
# pipver = None
# try:
#     import cryptography
#     has_crypto = True
# except ImportError:
#     # We'll try to install it. We set up the logic below.
#     try:
#         import pip
#         has_pip = True
#         # We'll use these to create a temporary lib path and remove it when done.
#         import sys
#         import tempfile
#     except ImportError:
#         # ABSOLUTE LAST fallback, if we got to THIS case, is to use subprocess.
#         has_pip = False
#         import subprocess
#
# # Try installing it then!
# if not all((has_crypto, )):
#     # venv only included after python 3.3.x. We fallback to subprocess if we can't do dis.
#     if sys.hexversion >= 0x30300f0:
#         has_ensurepip = False
#         import venv
#         if not has_pip and sys.hexversion >= 0x30400f0:
#             import ensurepip
#             has_ensurepip = True
#         temppath = tempfile.mkdtemp('_VENV')
#         v = venv.create(temppath)
#         if has_ensurepip and not has_pip:
#             # This SHOULD be unnecessary, but we want to try really hard.
#             ensurepip.bootstrap(root = temppath)
#             import pip
#             has_pip = True
#         if has_pip:
#             pipver = pip.__version__.split('.')
#             # A thousand people are yelling at me for this.
#             if int(pipver[0]) >= 10:
#                 from pip._internal import main as pipinstall
#             else:
#                 pipinstall = pip.main
#             if int(pipver[0]) >= 8:
#                 pipcmd = ['install',
#                           '--prefix={0}'.format(temppath),
#                           '--ignore-installed']
#             else:
#                 pipcmd = ['install',
#                           '--install-option="--prefix={0}"'.format(temppath),
#                           '--ignore-installed']
#             # Get the lib path.
#             libpath = os.path.join(temppath, 'lib')
#             if os.path.exists('{0}64'.format(libpath)) and not os.path.islink('{0}64'.format(libpath)):
#                 libpath += '64'
#             for i in os.listdir(libpath):  # TODO: make this more sane. We cheat a bit here by making assumptions.
#                 if re.search('python([0-9]+(\.[0-9]+)?)?$', i):
#                     libpath = os.path.join(libpath, i)
#                     break
#             libpath = os.path.join(libpath, 'site-packages')
#             sys.prefix = temppath
#             for m in ('cryptography', 'ed25519'):
#                 pipinstall(['install', 'cryptography'])
#             sys.path.append(libpath)
#             try:
#                 import cryptography
#                 has_crypto = True
#             except ImportError:  # All that trouble for nothin'. Shucks.
#                 pass
#
# if all((has_crypto, )):
#     pure_py = True
#
# if pure_py:
#     from cryptography.hazmat.primitives import serialization as crypto_serialization
#     from cryptography.hazmat.primitives.asymmetric import rsa
#     from cryptography.hazmat.backends import default_backend as crypto_default_backend
#

# We need static backup suffixes.
tstamp = int(datetime.datetime.utcnow().timestamp())

# TODO: associate various config directives with version, too.
# For now, we use this for primarily CentOS 6.x, which doesn't support ED25519 and probably some of the MACs.
# Bastards.
# https://ssh-comparison.quendi.de/comparison/cipher.html at some point in the future...
# TODO: maybe implement some parsing of the ssh -Q stuff? https://superuser.com/a/869005/984616
# If you encounter a version incompatibility, please let me know!
# nmap --script ssh2-enum-algos -PN -sV -p22 <host>
magic_ver = 6.5
ssh_ver = subprocess.run(['ssh', '-V'], stderr = subprocess.PIPE).stderr.decode('utf-8').strip().split()[0]
ssh_ver = float(re.sub('^(Open|Sun_)SSH_([0-9\.]+)(p[0-9]+)?,.*$', '\g<2>', ssh_ver))
if ssh_ver >= magic_ver:
    has_ed25519 = True
    supported_keys = ('ed25519', 'rsa')
else:
    has_ed25519 = False
    supported_keys = ('rsa', )


conf_options = {}
conf_options['sshd'] = {'KexAlgorithms': 'diffie-hellman-group-exchange-sha256',
                        'Protocol': '2',
                        'HostKey': ['/etc/ssh/ssh_host_rsa_key'],
                        #'PermitRootLogin': 'prohibit-password',  # older daemons don't like "prohibit-..."
                        'PermitRootLogin': 'without-password',
                        'PasswordAuthentication': 'no',
                        'ChallengeResponseAuthentication': 'no',
                        'PubkeyAuthentication': 'yes',
                        'Ciphers': 'aes256-ctr,aes192-ctr,aes128-ctr',
                        'MACs': 'hmac-sha2-512,hmac-sha2-256'}
if has_ed25519:
    conf_options['sshd']['HostKey'].append('/etc/ssh/ssh_host_ed25519_key')
    conf_options['sshd']['KexAlgorithms'] = ','.join(('curve25519-sha256@libssh.org',
                                                      conf_options['sshd']['KexAlgorithms']))
    conf_options['sshd']['Ciphers'] = ','.join((('chacha20-poly1305@openssh.com,'
                                                 'aes256-gcm@openssh.com,'
                                                 'aes128-gcm@openssh.com'),
                                                conf_options['sshd']['Ciphers']))
    conf_options['sshd']['MACs'] = ','.join((('hmac-sha2-512-etm@openssh.com,'
                                              'hmac-sha2-256-etm@openssh.com,'
                                              'umac-128-etm@openssh.com'),
                                             conf_options['sshd']['MACs'],
                                             'umac-128@openssh.com'))
# Uncomment if this is further configured
#conf_options['sshd']['AllowGroups'] = 'ssh-user'

conf_options['ssh'] = {'Host': {'*': {'KexAlgorithms': 'diffie-hellman-group-exchange-sha256',
                                      'PubkeyAuthentication': 'yes',
                                      'HostKeyAlgorithms': 'ssh-rsa'}}}
if has_ed25519:
    conf_options['ssh']['Host']['*']['KexAlgorithms'] = ','.join(('curve25519-sha256@libssh.org',
                                                                  conf_options['ssh']['Host']['*']['KexAlgorithms']))
    conf_options['ssh']['Host']['*']['HostKeyAlgorithms'] = ','.join(
                                                            (('ssh-ed25519-cert-v01@openssh.com,'
                                                              'ssh-rsa-cert-v01@openssh.com,'
                                                              'ssh-ed25519'),
                                                             conf_options['ssh']['Host']['*']['HostKeyAlgorithms']))


def hostKeys(buildmoduli):
    # Starting haveged should help lessen the time load a non-negligible amount, especially on virtual platforms.
    if os.path.lexists('/usr/bin/haveged'):
        # We could use psutil here, but then that's a python dependency we don't need.
        # We could parse the /proc directory, but that's quite unnecessary. pgrep's installed by default on
        # most distros.
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
            os.rename(k, '{0}.old.{1}'.format(k, tstamp))
    if has_ed25519:
        subprocess.run(['ssh-keygen', '-t', 'ed25519', '-f', '/etc/ssh/ssh_host_ed25519_key', '-q', '-N', ''])
    subprocess.run(['ssh-keygen', '-t', 'rsa', '-b', '4096', '-f', '/etc/ssh/ssh_host_rsa_key', '-q', '-N', ''])
    # We currently don't use this, but for simplicity's sake let's return the host keys.
    hostkeys = {}
    for k in supported_keys:
        with open('/etc/ssh/ssh_host_{0}_key.pub'.format(k), 'r') as f:
            hostkeys[k] = f.read()
    return(hostkeys)

def config(opts, t):
    special = {'sshd': {}, 'ssh': {}}
    # We need to handle these directives a little differently...
    special['sshd']['opts'] = ['Match']
    special['sshd']['filters'] = ['User', 'Group', 'Host', 'LocalAddress', 'LocalPort', 'Address']
    # These are arguments supported by each of the special options. We'll use this to verify entries.
    special['sshd']['args'] = ['AcceptEnv', 'AllowAgentForwarding', 'AllowGroups', 'AllowStreamLocalForwarding',
                               'AllowTcpForwarding', 'AllowUsers', 'AuthenticationMethods', 'AuthorizedKeysCommand',
                               'AuthorizedKeysCommandUser', 'AuthorizedKeysFile', 'AuthorizedPrincipalsCommand',
                               'AuthorizedPrincipalsCommandUser', 'AuthorizedPrincipalsFile', 'Banner',
                               'ChrootDirectory', 'ClientAliveCountMax', 'ClientAliveInterval', 'DenyGroups',
                               'DenyUsers', 'ForceCommand', 'GatewayPorts', 'GSSAPIAuthentication',
                               'HostbasedAcceptedKeyTypes', 'HostbasedAuthentication',
                               'HostbasedUsesNameFromPacketOnly', 'IPQoS', 'KbdInteractiveAuthentication',
                               'KerberosAuthentication', 'MaxAuthTries', 'MaxSessions', 'PasswordAuthentication',
                               'PermitEmptyPasswords', 'PermitOpen', 'PermitRootLogin', 'PermitTTY', 'PermitTunnel',
                               'PermitUserRC', 'PubkeyAcceptedKeyTypes', 'PubkeyAuthentication', 'RekeyLimit',
                               'RevokedKeys', 'StreamLocalBindMask', 'StreamLocalBindUnlink', 'TrustedUserCAKeys',
                               'X11DisplayOffset', 'X11Forwarding', 'X11UseLocalHost']
    special['ssh']['opts'] = ['Host', 'Match']
    special['ssh']['args'] = ['canonical', 'exec', 'host', 'originalhost', 'user', 'localuser']
    cf = '/etc/ssh/{0}_config'.format(t)
    shutil.copy2(cf, '{0}.bak.{1}'.format(cf, tstamp))
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
                # If I was more worried about recursion, or if I was appending here, I should use conf[:].
                # But I'm not. So I won't.
                for idx, opt in enumerate(conf):
                    if re.match('^{0}(\s.*)?\n$'.format(o), opt):
                        conf[idx] = '#{0}'.format(opt)
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
    if has_ed25519:
        if not os.path.lexists('{0}/id_ed25519'.format(sshdir)) \
                and not os.path.lexists('{0}/id_ed25519.pub'.format(sshdir)):
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
    for k in supported_keys:
        with open('{0}/id_{1}.pub'.format(sshdir, k), 'r') as f:
            pubkeys[user][k] = f.read()
    return(pubkeys)

def daemonMgr():
    # We're about to do somethin' stupid. Let's make it a teeny bit less stupid.
    with open(os.devnull, 'w') as devnull:
        confchk = subprocess.run(['sshd', '-T'], stdout = devnull)
    if confchk.returncode != 0:
        for suffix in ('', '.pub'):
            for k in glob.glob('/etc/ssh/ssh_host_*key{0}'.format(suffix)):
                os.rename('{0}.old.{1}'.format(k, tstamp), k)
            for conf in ('', 'd'):
                cf = '/etc/ssh/ssh{0}_config'.format(conf)
                os.rename('{0}.{1}'.format(cf, tstamp),
                          cf)
        exit('OOPS. We goofed. Backup restored and bailing out.')
    pidfile = '/var/run/sshd.pid'
    # We need to restart sshd once we're done. I feel dirty doing this, but this is the most cross-platform way I can
    # do it. First, we need the path to the PID file.
    # TODO: do some kind of better way of doing this.
    with open('/etc/ssh/sshd_config', 'r') as f:
        for line in f.readlines():
            if re.search('^\s*PidFile\s+.*', line):
                pidfile = re.sub('^\s*PidFile\s+(.*)(#.*)?$', '\g<1>', line)
                break
    with open(pidfile, 'r') as f:
        pid = int(f.read().strip())
    os.kill(pid, signal.SIGHUP)
    return()

def main():
    _chkfile = '/etc/ssh/.aif-generated'
    if not os.path.isfile(_chkfile):
        # Warning: The moduli stuff can take a LONG time to run. Hours.
        buildmoduli = True
        hostKeys(buildmoduli)
        restart = True
    for t in ('sshd', 'ssh'):
        config(conf_options[t], t)
    clientKeys()
    with open(_chkfile, 'w') as f:
        f.write(('ssh, sshd, and hostkey configurations/keys have been modified by sshsecure.py from OpTools.\n'
                 'https://git.square-r00t.net/OpTools/\n'))
    daemonMgr()
    return()

if __name__ == '__main__':
    main()
