#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
##
import magic  # From http://darwinsys.com/file/, not https://github.com/ahupp/python-magic
import psutil
from lxml import etree


    # def get_file_kernel_ver(self, kpath):
    #     # Gets the version of a kernel file.
    #     kpath = os.path.abspath(os.path.expanduser(kpath))
    #     _kinfo = {}
    #     with open(kpath, 'rb') as f:
    #         _m = magic.detect_from_content(f.read())
    #     for i in _m.name.split(','):
    #         l = i.strip().split()
    #         # Note: this only grabs the version number.
    #         # If we want to get e.g. the build user/machine, date, etc.,
    #         # then we need to join l[1:].
    #         # We technically don't even need a dict, either. We can just iterate.
    #         # TODO.
    #         _kinfo[l[0].lower()] = (l[1] if len(l) > 1 else None)
    #     if 'version' not in _kinfo:
    #         raise RuntimeError('Cannot deterimine the version of {0}'.format(
    #                 kpath))
    #     else:
    #         return (_kinfo['version'])

class BootSync(object):
    def __init__(self, cfg = None, *args, **kwargs):
        if not cfg:
            self.cfgfile = '/etc/bootsync.xml'
        else:
            self.cfgfile = os.path.abspath(os.path.expanduser(cfg))
        self.ns = '{http://git.square-r00t.net/OpTools/tree/sys/BootSync/}'
        self.cfg = None
        self.xml = None
        # This is the current live kernel.
        self.currentKernVer = self._getRunningKernel()
        # This is the installed kernel from the package manager.
        self.kernelFile = None
        self.installedKernVer = None
        self.RequireReboot = False  # If a reboot is needed (WARN, don't execute!)
        self.blkids = {}
        self.dummy_uuid = None
        self.syncs = {}
        ##
        self.getCfg()
        self.chkMounts()
        self.chkReboot()
        self.getHashes()
        self.getBlkids()
        # self.sync()
        # self.writeConfs()

    def getCfg(self):
        if not os.path.isfile(self.cfgfile):
            raise FileNotFoundError('Configuration file {0} does not exist!'.format(self.cfgfile))
        try:
            with open(self.cfgfile, 'rb') as f:
                self.xml = etree.parse(f)
            self.xml.xinclude()
            self.cfg = self.xml.getroot()
        except etree.XMLSyntaxError:
            # self.logger.error('{0} is invalid XML'.format(self.cfgfile))
            raise ValueError(('{0} does not seem to be valid XML. '
                              'See sample.config.xml for an example configuration.').format(self.cfgfile))
        return()

    def chkMounts(self):
        _mounts = {m.device: m.mountpoint for m in psutil.disk_partitions(all = True)}
        for esp in self.cfg.findall('{0}partitions/{0}part'.format(self.ns)):
            disk = esp.attrib['path']
            mount = os.path.abspath(os.path.expanduser(esp.attrib['mount']))
            if not os.path.isdir(mount):
                os.makedirs(mount, exist_ok = True)
            if disk not in _mounts:
                with open(os.devnull, 'w') as devnull:
                    c = subprocess.run(['/usr/bin/mount', mount],
                                       stderr = devnull)
                    if c.returncode == 1:  # Not specified in fstab
                        subprocess.run(['/usr/bin/mount', disk, mount],
                                       stderr = devnull)
                    elif c.returncode == 32:  # Already mounted
                        pass
        return()

    def chkReboot(self):
        self._getInstalledKernel()
        if not self.kernelFile:
            return()  # No isKernel="true" was specified in the config.
        if self.installedKernVer != self.currentKernVer:
            self.RequireReboot = True
            # TODO: logger instead?
            print(('NOTE: REBOOT REQUIRED. '
                   'New kernel is {0}. '
                   'Running kernel is {1}.').format(self.installedKernVer,
                                                   self.currentKernVer))
        return()

    def getBlkids(self):
        c = subprocess.run(['/usr/bin/blkid',
                            '-o', 'export'],
                           stdout = subprocess.PIPE)
        if c.returncode != 0:
            raise RuntimeError('Could not fetch block ID information')
        for p in c.stdout.decode('utf-8').split('\n\n'):
            line = [i.strip() for i in p.splitlines()]
            d = dict(map(lambda i: i.split('='), line))
            if d.get('TYPE') == 'squashfs':
                continue
            self.blkids[d['DEVNAME']] = d.get('PARTUUID', d['UUID'])
        c = subprocess.run(['/usr/bin/findmnt',
                            '--json',
                            '-T', '/boot'],
                           stdout = subprocess.PIPE)
        # I write ridiculous one-liners.
        self.dummy_uuid = self.blkids[json.loads(c.stdout.decode('utf-8'))['filesystems'][0]['source']]
        return()

    def getHashes(self):
        def _get_hash(fpathname):
            fpathname = os.path.abspath(os.path.expanduser(fpathname))
            _hash = hashlib.sha512()
            with open(fpathname, 'rb') as fh:
                _hash.update(fh.read())
            return(_hash.hexdigest())
        for f in self.cfg.findall('{0}fileChecks/{0}file'):
            # We do /boot files manually in case it isn't specified as a
            # separate mount.
            rel_fpath = f.text
            fpath = os.path.join('/boot', rel_fpath)
            canon_hash = _get_hash(fpath)
            for esp in self.cfg.findall('{0}partitions/{0}part'.format(self.ns)):
                mount = os.path.abspath(os.path.expanduser(esp.attrib['mount']))
                new_fpath = os.path.join(mount, f)
                file_hash = _get_hash(new_fpath)
                if file_hash != canon_hash:
                    if rel_fpath not in self.syncs:
                        self.syncs[rel_fpath] = []
                    self.syncs[rel_fpath].append(mount)
        return()

    def sync(self, dryrun = False, *args, **kwargs):
        if not dryrun:
            if os.geteuid() != 0:
                raise PermissionError('You must be root to write to the appropriate destinations')
        for f in self.syncs:
            for m in self.syncs[f]:
                orig = os.path.join('/boot', f)
                dest = os.path.join(m, f)
                if not dryrun:
                    shutil.copy2(orig, dest)
        bootmounts = [e.attrib['mount'] for e in self.cfg.findall('{0}partitions/{0}part'.format(self.ns))]
        # syncPaths
        for syncpath in self.cfg.findall('{0}syncPaths/{0}path'.format(self.ns)):
            source = os.path.abspath(os.path.expanduser(syncpath.attrib['source']))
            target = syncpath.attrib['target']
            pattern = syncpath.attrib['pattern']
            # We don't use filecmp for this because:
            # - dircmp doesn't recurse
            # - the reports/lists don't retain relative paths
            # - we can't regex out files
            for root, dirs, files in os.walk(source):
                prefix = re.sub('\/?{0}\/?'.format(source), '', root)
                ptrn = re.compile(pattern)
                for f in files:
                    fname_path = os.path.join(prefix, f)
                    bootsource = os.path.join(source, fname_path)
                    boottarget = os.path.join(target, fname_path)
                    if ptrn.search(f):
                        # Compare the contents.
                        with open(bootsource, 'rb') as fh:
                            orig_hash = hashlib.sha512(fh.read()).hexdigest()
                        for bootdir in bootmounts:
                            bootfile = os.path.join(bootdir, boottarget)
                            if not dryrun:
                                if not os.path.isfile(bootfile):
                                    os.makedirs(os.path.dirname(bootfile),
                                                exist_ok = True)
                                    shutil.copy2(bootsource, bootfile)
                                else:
                                    with open(bootfile, 'rb') as fh:
                                        dest_hash = hashlib.sha512(fh.read()).hexdigest()
                                    if orig_hash != dest_hash:
                                        shutil.copy2(bootsource, bootfile)
        # fileChecks are a *lot* easier.
        for f in self.cfg.findall('{0}fileChecks/{0}file'.format(self.ns)):
            source = os.path.join('/boot', f.text)
            with open(source, 'rb') as fh:
                orig_hash = hashlib.sha512(fh.read()).hexdigest()
            for bootdir in bootmounts:
                bootfile = os.path.join(bootdir, f.text)
                if not dryrun:
                    if not os.path.isfile(bootfile):
                        os.makedirs(os.path.dirname(bootfile),
                                    exist_ok = True)
                        shutil.copy2(source, bootfile)
                    else:
                        with open(bootfile, 'rb') as fh:
                            dest_hash = hashlib.sha512(fh.read()).hexdigest()
                        if orig_hash != dest_hash:
                            shutil.copy2(source, bootfile)
        return()


    def writeConfs(self, dryrun = False, *args, **kwargs):
        if not dryrun:
            if os.geteuid() != 0:
                raise PermissionError('You must be root to write to the appropriate destinations')
        else:
            return()
        # Get a fresh config in place.
        with open(os.devnull, 'wb') as DEVNULL:
            c = subprocess.run(['/usr/bin/grub-mkconfig',
                                '-o', '/boot/grub/grub.cfg'],
                               stdout = DEVNULL,
                               stderr = DEVNULL)
        if c.returncode != 0:
            raise RuntimeError('An error occurred when generating the GRUB configuration file.')
        with open('/boot/grub/grub.cfg', 'r') as f:
            _grubcfg = f.read()
        for esp in self.cfg.findall('{0}partitions/{0}part'.format(self.ns)):
            mount = os.path.abspath(os.path.expanduser(esp.attrib['mount']))
            disk = os.path.abspath(os.path.expanduser(esp.attrib['path']))
            with open(os.path.join(mount, 'grub/grub.cfg'), 'w') as f:
                for line in _grubcfg.splitlines():
                    # if re.search(r'^\s*search\s+(.*)\s(-u|--fs-uuid)', line):
                    #     pass
                    i = re.sub(r'(?<!\=UUID\=){0}'.format(self.dummy_uuid),
                               self.blkids[disk],
                               line)
                    # If the array is in a degraded state, this will still let us at LEAST boot.
                    i = re.sub(r'\s+--hint=[\'"]?mduuid/[a-f0-9]{32}[\'"]?', '', i)
                    f.write('{0}\n'.format(i))
        return()

    def _getRunningKernel(self):
        _vers = []
        # If we change the version string capture in get_file_kernel_ver(),
        # this will need to be expanded as well.
        # Really we only need to pick one, but #YOLO; why not sanity-check.
        # ALL of these should match, hence the reduction with set() down to (what SHOULD be) just 1 item.
        _vers.append(os.uname().release)
        _vers.append(platform.release())
        _vers.append(platform.uname().release)
        _vers = sorted(list(set(_vers)))
        if len(_vers) != 1:
            raise RuntimeError('Cannot reliably determine current running kernel version!')
        else:
            return(_vers[0])

    def _getInstalledKernel(self):
        # Could we maybe remove the dependency for the "magic" module with a struct?
        # http://lxr.linux.no/#linux+v2.6.39/Documentation/x86/boot.txt
        # https://stackoverflow.com/a/11179559/733214
        try:
            len(self.cfg)
        except TypeError:
            raise RuntimeError('Tried to find the isKernel with no config set up and parsed')
        for f in self.cfg.findall('{0}fileChecks/{0}file'.format(self.ns)):
            isKernel = (True
                            if f.attrib.get('isKernel', 'false').lower() in ('true', '1')
                        else
                            False)
            if isKernel:
                self.kernelFile = f.text
        if self.kernelFile:
            with open(os.path.join('/boot', self.kernelFile), 'rb') as fh:
                magicname = magic.detect_from_content(fh.read())
            names = [i.strip().split(None, 1) for i in magicname.name.split(',') if i.strip() != '']
            for n in names:
                if len(n) != 2:
                    continue
                k, v = n
                # Note: this only grabs the version number.
                # If we want to get e.g. the build user/machine, date, etc.,
                # then we need to do a join. Shouldn't be necessary, though.
                if k.lower() == 'version':
                    self.installedKernVer = v.split(None, 1)[0]
        return()

def parseArgs():
    args = argparse.ArgumentParser(description = ('Sync files to assist using mdadm RAID arrays with UEFI'))
    args.add_argument('-c', '--cfg',
                      dest = 'cfg',
                      default = '/etc/bootsync.xml',
                      help = ('The path to the bootsync configuration file. Default is /etc/bootsync.xml'))
    args.add_argument('-n', '--dry-run',
                      dest = 'dryrun',
                      action = 'store_true',
                      help = ('If specified, don\'t write any changes'))
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    bs = BootSync(**args)
    bs.sync(**args)
    bs.writeConfs(**args)
    return()

if __name__ == '__main__':
    main()
