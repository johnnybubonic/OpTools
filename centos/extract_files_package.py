#!/usr/bin/env python

# Supports CentOS 6.9 and up, untested on lower versions.
# Lets you extract files for a given package name(s) without installing
# any extra packages (such as yum-utils for repoquery).

# NOTE: If you're on CentOS 6.x, since it uses such an ancient version of python you need to either install
# python-argparse OR just resign to using it for all packages with none of the features.
try:
    import argparse
    has_argparse = True
except ImportError:
    has_argparse = False
import os
import re
import shutil
import tempfile
# For when CentOS/RHEL switch to python 3 by default (if EVER).
import sys
pyver = sys.version_info
try:
    import yum
    # Needed for verbosity
    from yum.logginglevels import __NO_LOGGING as yum_nolog
    has_yum = True
except ImportError:
    has_yum = False
    exit('This script only runs on the system-provided Python on RHEL/CentOS/other RPM-based distros.')
try:
    # pip install libarchive
    # https://github.com/dsoprea/PyEasyArchive
    import libarchive.public as lap
    is_ctype = False
except ImportError:
    try:
        # pip install libarchive
        # https://github.com/Changaco/python-libarchive-c
        import libarchive
        if 'file_reader' in dir(libarchive):
            is_legacy = False
        else:
            # https://code.google.com/archive/p/python-libarchive
            is_legacy = True
        is_ctype = True
    except ImportError:
        raise ImportError('Try yum -y install python-libarchive')


class FileExtractor(object):
    def __init__(self, dest_dir, paths, verbose = False, *args, **kwargs):
        self.dest_dir = os.path.abspath(os.path.expanduser(dest_dir))
        self.verbose = verbose  # TODO: print file name as extracting? Verbose as argument?
        self.rpms = {}
        if 'pkgs' in kwargs and kwargs['pkgs']:
            self.pkgs = kwargs['pkgs']
            self.yum_getFiles()
        if 'rpm_files' in kwargs and kwargs['rpm_files']:
            self.rpm_files = kwargs['rpm_files']
            self.getFiles()
        if '*' in paths:
            self.paths = None
        else:
            self.paths = [re.sub('^', '.', os.path.abspath(i)) for i in paths]

    def yum_getFiles(self):
        import logging
        yumloggers = ['yum.filelogging.RPMInstallCallback', 'yum.verbose.Repos', 'yum.verbose.plugin', 'yum.Depsolve',
                      'yum.verbose', 'yum.plugin', 'yum.Repos', 'yum', 'yum.verbose.YumBase', 'yum.filelogging',
                      'yum.verbose.YumPlugins', 'yum.RepoStorage', 'yum.YumBase', 'yum.filelogging.YumBase',
                      'yum.verbose.Depsolve']
        # This actually silences everything. Nice.
        # https://stackoverflow.com/a/46716482/733214
        if not self.verbose:
            for loggerName in yumloggers:
               logger = logging.getLogger(loggerName)
               logger.setLevel(yum_nolog)
        # http://yum.baseurl.org/api/yum/yum/__init__.html#yumbase
        yb = yum.YumBase()
        yb.conf.downloadonly = True
        yb.conf.downloaddir = os.path.join(self.dest_dir, '.CACHE')
        yb.conf.quiet = True
        yb.conf.assumeyes = True
        for pkg in self.pkgs:
            try:
                p = yb.reinstall(name = pkg)
            except yum.Errors.ReinstallRemoveError:
                p = yb.install(name = pkg)
            p = p[0]
            # I am... not 100% certain on this. Might be a better way?
            fname = '{0}-{3}-{4}.{1}.rpm'.format(*p.pkgtup)
            self.rpms[pkg] =  os.path.join(yb.conf.downloaddir, fname)
        yb.buildTransaction()
        try:
            yb.processTransaction()
        except SystemExit:
            pass  # It keeps passing an exit because it's downloading only. Get it together, RH.
        yb.closeRpmDB()
        yb.close()
        return()

    def getFiles(self):
        for rf in self.rpm_files:
            # TODO: check if we have the rpm module and if so, rip pkg name from it? use that as key instead of rf?
            self.rpms[os.path.basename(rf)] = os.path.abspath(os.path.expanduser(rf))
        return()

    def extractFiles(self):
        # If we have yum, we can, TECHNICALLY, do this with:
        # http://yum.baseurl.org/api/yum/rpmUtils/miscutils.html#rpmUtils.miscutils.rpm2cpio
        # But nope. We can't selectively decompress members based on path with rpm2cpio-like funcs.
        # We keep getting extraction artefacts, at least with legacy libarchive_c, so we use a hammer.
        _curdir = os.getcwd()
        _tempdir = tempfile.mkdtemp()
        os.chdir(_tempdir)
        for rpm_file in self.rpms:
            rf = self.rpms[rpm_file]
            if is_ctype:
                if not is_legacy:
                    # ctype - extracts to pwd
                    with libarchive.file_reader(rf) as reader:
                        for entry in reader:
                            if self.paths and entry.path not in self.paths:
                                continue
                            if entry.isdir():
                                continue
                            fpath = os.path.join(self.dest_dir, rpm_file, entry.path)
                            if not os.path.isdir(os.path.dirname(fpath)):
                                os.makedirs(os.path.dirname(fpath))
                            with open(fpath, 'wb') as f:
                                for b in entry.get_blocks():
                                    f.write(b)
                else:
                    with libarchive.Archive(rf) as reader:
                        for entry in reader:
                            if (self.paths and entry.pathname not in self.paths) or (entry.isdir()):
                                continue
                            fpath = os.path.join(self.dest_dir, rpm_file, entry.pathname)
                            if not os.path.isdir(os.path.dirname(fpath)):
                                os.makedirs(os.path.dirname(fpath))
                            reader.readpath(fpath)
            else:
                # pyEasyArchive/"pypi/libarchive"
                with lap.file_reader(rf) as reader:
                    for entry in reader:
                        if (self.paths and entry.pathname not in self.paths) or (entry.filetype.IFDIR):
                            continue
                        fpath = os.path.join(self.dest_dir, rpm_file, entry.pathname)
                        if not os.path.isdir(os.path.dirname(fpath)):
                            os.makedirs(os.path.dirname(fpath))
                        with open(fpath, 'wb') as f:
                            for b in entry.get_blocks():
                                f.write(b)
        os.chdir(_curdir)
        shutil.rmtree(_tempdir)
        return()

def parseArgs():
    args = argparse.ArgumentParser(description = ('This script allows you to extract files for a given package '
                                                  '{0}without installing any extra packages (such as yum-utils '
                                                  'for repoquery). '
                                                  'You must use at least one -r/--rpm{1}.').format(
                                                                        ('name(s) ' if has_yum else ''),
                                                                        (', -p/--package, or both' if has_yum else '')))
    args.add_argument('-d', '--dest-dir',
                      dest = 'dest_dir',
                      default = '/var/tmp/rpm_extract',
                      help = ('The destination for the extracted package file tree (in the format of '
                              '<dest_dir>/<pkg_nm>/<tree>). '
                              'Default: /var/tmp/rpm_extract'))
    args.add_argument('-r', '--rpm',
                      dest = 'rpm_files',
                      metavar = 'PATH/TO/RPM',
                      action = 'append',
                      default = [],
                      help = ('If specified, use this RPM file instead of the system\'s RPM database. Can be '
                              'specified multiple times'))
    if has_yum:
        args.add_argument('-p', '--package',
                          dest = 'pkgs',
                          #nargs = 1,
                          metavar = 'PKGNAME',
                          action = 'append',
                          default = [],
                          help = ('If specified, restrict the list of packages to check against to only this package. '
                                  'Can be specified multiple times. HIGHLY RECOMMENDED'))
    args.add_argument('paths',
                      nargs = '+',
                      metavar = 'path/file/name.ext',
                      help = ('The path(s) of files to extract. If \'*\' is used, extract all files'))
    return(args)

def main():
    if has_argparse:
        args = vars(parseArgs().parse_args())
        args['rpm_files'] = [os.path.abspath(os.path.expanduser(i)) for i in args['rpm_files']]
        if not any((args['rpm_files'], args['pkgs'])):
            exit(('You have not specified any package files{0}.\n'
                  'This is so dumb we are bailing out.\n').format((' or package names') if has_yum else ''))
    else:
        raise RuntimeError('Please yum -y install python-argparse')
    fe = FileExtractor(**args)
    fe.extractFiles()
    return()

if __name__ == '__main__':
    main()
