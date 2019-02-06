#!/usr/bin/env python

import hashlib
import json
# From http://darwinsys.com/file/, not https://github.com/ahupp/python-magic
import magic
import os
import platform
import psutil
import re
import shutil
import subprocess

# The device:mountpoint of the mounts for the failover partitions.
mounts = {'/dev/sdb1': '/mnt/boot1',
          '/dev/sdd1': '/mnt/boot2'}
# The files we checksum.
files = ['initramfs-linux.img', 'intel-ucode.img', 'memtest86+/memtest.bin',
         'vmlinuz-linux']
# These paths are used to ensure an up-to-date grub.
grub = {'themes': {'orig': '/usr/share/grub/themes',
                   'dest': 'grub/themes',
                   'pattern': '.*'},
        'modules': {'orig': '/usr/lib/grub/x86_64-efi',
                    'dest': 'grub/x86_64-efi',
                    'pattern': '^.*\.(mod|lst|sh)$'},
        'isos': {'orig': '/boot/iso',
                 'dest': 'iso',
                 'pattern': '^.*\.(iso|img)$'}}

###############################################################################
# NOTE:
# If I need to rebuild,
# efibootmgr -c -d /dev/<PRIMARY DEVICE> -p <PARTITION NUMBER> \
#       -l /EFI/Arch/grubx64.efi -L Arch
# efibootmgr -c -d /dev/<FALLBACK DEVICE> -p <PARTITION NUMBER> \
#       -l /EFI/Arch/grubx64.efi -L 'Arch (Fallback)'
# And don't forget to install grub.
# grub-install --boot-directory=/mnt/boot1 --bootloader-id=Arch \
#       --efi-directory=/mnt/boot1/ --target=x86_64-efi --no-nvram  --recheck
# grub-install --boot-directory=/mnt/boot2 --bootloader-id=Arch \
#       --efi-directory=/mnt/boot2/ --target=x86_64-efi --no-nvram  --recheck
# You need to have grub's config set to use UUIDs.
###############################################################################

def get_file_kernel_ver(kpath):
    # Gets the version of a kernel file.
    kpath = os.path.abspath(os.path.expanduser(kpath))
    _kinfo = {}
    with open(kpath, 'rb') as f:
        _m = magic.detect_from_content(f.read())
    for i in _m.name.split(','):
        l = i.strip().split()
        # Note: this only grabs the version number.
        # If we want to get e.g. the build user/machine, date, etc.,
        # then we need to join l[1:].
        # We technically don't even need a dict, either. We can just iterate.
        # TODO.
        _kinfo[l[0].lower()] = (l[1] if len(l) > 1 else None)
    if 'version' not in _kinfo:
        raise RuntimeError('Cannot deterimine the version of {0}'.format(
                                                                        kpath))
    else:
        return(_kinfo['version'])

def get_cur_kernel_ver():
    _vers = []
    # If we change the version string capture in get_file_kernel_ver(),
    # this will need to be expanded as well.
    # Really we only need to pick one, but #YOLO; why not sanity-check.
    _vers.append(os.uname().release)
    _vers.append(platform.release())
    _vers.append(platform.uname().release)
    _vers = sorted(list(set(_vers)))
    if len(_vers) != 1:
        raise RuntimeError('Cannot reliably determine current running '
                           'kernel version!')
    else:
        return(_vers[0])

class BootSync(object):
    def __init__(self):
        self.chk_mounts()
        # This is the current live kernel.
        self.cur_kern_ver = get_cur_kernel_ver()
        # This is the installed kernel from Pacman.
        self.installed_kern_ver = get_file_kernel_ver('/boot/vmlinuz-linux')
        self.reboot = False  # If a reboot is needed (WARN, don't execute!)
        self.syncs = {}
        self.blkids = {}
        self.dummy_uuid = None
        self.chk_reboot()
        self.get_hashes()
        self.get_blkids()
        self.sync()

    def chk_mounts(self):
        _mounts = {m.device:m.mountpoint for m in \
                                            psutil.disk_partitions(all = True)}
        for m in mounts:
            mntpt = os.path.abspath(os.path.expanduser(mounts[m]))
            if not os.path.isdir(mntpt):
                os.makedirs(mntpt, exist_ok = True)
            if m not in _mounts:
                with open(os.devnull, 'w') as devnull:
                    c = subprocess.run(['/usr/bin/mount', mounts[m]], stderr = devnull)
                    if c.returncode == 1:  # Not specified in fstab
                        subprocess.run(['/usr/bin/mount', m, mntpt], stderr = devnull)
                    elif c.returncode == 32:  # Already mounted
                        pass
        return()

    def chk_reboot(self):
        if self.installed_kern_ver != self.cur_kern_ver:
            self.reboot = True
            print(
                'NOTE: REBOOT REQUIRED. New kernel is {0}. Running kernel is '
                '{1}.'.format(self.installed_kern_ver, self.cur_kern_ver))
        return()

    def get_blkids(self):
        c = subprocess.run(['/usr/bin/blkid',
                            '-o', 'export'],
                           stdout = subprocess.PIPE)
        if c.returncode != 0:
            raise RuntimeError('Could not fetch block ID information')
        for p in c.stdout.decode('utf-8').split('\n\n'):
            line = [i.strip() for i in p.splitlines()]
            d = dict(map(lambda i : i.split('='), line))
            if 'PARTUUID' in d:
                self.blkids[d['DEVNAME']] = d['PARTUUID']
            else:
                self.blkids[d['DEVNAME']] = d['UUID']
        c = subprocess.run(['/usr/bin/findmnt',
                            '--json',
                            '-T', '/boot'],
                           stdout = subprocess.PIPE)
        # I write ridiculous one-liners.
        self.dummy_uuid = self.blkids[json.loads(
                            c.stdout.decode(
                                    'utf-8'
                                    )
                            )['filesystems'][0]['source']]
        return()

    def get_hashes(self):
        def _get_hash(fpath):
            fpath = os.path.abspath(os.path.expanduser(fpath))
            _hash = hashlib.sha512()
            with open(fpath, 'rb') as fh:
                _hash.update(fh.read())
            return(_hash.hexdigest())
        for f in files:
            # We do /boot files manually in case it isn't specified as a
            # separate mount.
            fpath = os.path.join('/boot', f)
            canon_hash = _get_hash(fpath)
            for m in mounts:
                fpath = os.path.join(mounts[m], f)
                file_hash = _get_hash(fpath)
                if file_hash != canon_hash:
                    if f not in self.syncs:
                        self.syncs[f] = []
                    self.syncs[f].append(mounts[m])
        return()

    def sync(self):
        # NOTE: We *may* be able to get away with instead just doing the above
        # grub-install commands to each of the boot disks.
        for f in self.syncs:
            for m in self.syncs[f]:
                orig = os.path.join('/boot', f)
                dest = os.path.join(m, f)
                shutil.copy2(orig, dest)
        _mounts = list(mounts.values()) + ['/boot']
        for g in grub:
            _fnames = []
            # We don't use filecmp for this because:
            # - dircmp doesn't recurse
            # - the reports/lists don't retain relative paths
            # - we can't regex out files
            for root, dirs, files in os.walk(grub[g]['orig']):
                prefix = re.sub('\/?{0}\/?'.format(grub[g]['orig']), '', root)
                ptrn = re.compile(grub[g]['pattern'])
                for f in files:
                    if ptrn.search(f):
                        _fnames.append(os.path.join(prefix, f))
            # If we want to delete files in the destination that don't exist in
            # the original, here's where we would do it.
            # for root, dirs, files in os.walk(grub[g]['dest']):
            #     _pre_prefix = re.sub('\/?$', '', grub[g]['dest'])
            #     prefix = re.sub(_pre_prefix, '', root)
            #     #ptrn = re.compile(grub[g]['pattern'])
            #     for f in files:
            #         _p = os.path.join(prefix, f)
            #         if _p not in _fnames:
            #             os.remove(os.path.join(grub[g]['dest'], _p))
            # Now we compare the contents.
            for f in _fnames:
                origfile = os.path.join(grub[g]['orig'], f)
                destfile = os.path.join(grub[g]['dest'], f)
                with open(origfile, 'rb') as f:
                    _orig = hashlib.sha512(f.read()).hexdigest()
                for m in _mounts:
                    real_destfile = os.path.join(m, destfile)
                    if not os.path.isfile(real_destfile):
                        os.makedirs(os.path.dirname(real_destfile),
                                    exist_ok = True)
                        shutil.copy2(origfile, real_destfile)
                    else:
                        with open(real_destfile, 'rb') as f:
                            _dest = hashlib.sha512(f.read()).hexdigest()
                        if _orig != _dest:
                            shutil.copy2(origfile, real_destfile)
        return()


    def write_confs(self):
        # Get a fresh config in place.
        with open(os.devnull, 'wb') as DEVNULL:
            c = subprocess.run(['/usr/bin/grub-mkconfig',
                                '-o', '/boot/grub/grub.cfg'],
                               stdout = DEVNULL,
                               stderr = DEVNULL)
        if c.returncode != 0:
            raise RuntimeError('An error occurred when generating the GRUB '
                               'configuration file.')
        with open('/boot/grub/grub.cfg', 'r') as f:
            _grubcfg = f.read()
        for d in mounts:
            with open(os.path.join(mounts[d], 'grub/grub.cfg'), 'w') as f:
                for line in _grubcfg.splitlines():
                    i = re.sub('(?<!\=UUID\=){0}'.format(self.dummy_uuid),
                               self.blkids[d],
                               line)
                    i = re.sub('\s--hint=\'mduuid\/[a-f0-9]{32}\'', '', i)
                    f.write('{0}\n'.format(i))
        return()

def main():
    if os.geteuid() != 0:
        exit('You must be root to run this!')
    bs = BootSync()
    bs.sync()
    bs.write_confs()
    return()

if __name__ == '__main__':
    main()
