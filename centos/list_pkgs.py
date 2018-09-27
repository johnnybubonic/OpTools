#!/usr/bin/env python

# Supports CentOS 6.9 and up, untested on lower versions.
# Lets you dump a list of installed packages for backup purposes
# Reference: https://blog.fpmurphy.com/2011/08/programmatically-retrieve-rpm-package-details.html

import argparse
import copy
import datetime
import io
import re
import sys
try:
    import yum
except ImportError:
    exit('This script only runs on RHEL/CentOS/other yum-based distros.')
# Detect RH version.
ver_re = re.compile('^(centos( linux)? release) ([0-9\.]+) .*$', re.IGNORECASE)
# distro module isn't stdlib, and platform.linux_distribution() (AND platform.distro()) are both deprecated in 3.7.
# So we get hacky.
with open('/etc/redhat-release', 'r') as f:
    ver = [int(i) for i in ver_re.sub('\g<3>', f.read().strip()).split('.')]
import pprint

repo_re = re.compile('^@')

class PkgIndexer(object):
    def __init__(self, **args):
        self.pkgs = []
        self.args = args
        self.yb = yum.YumBase()
        # Make the Yum API shut the heck up.
        self.yb.preconf.debuglevel = 0
        self.yb.preconf.errorlevel = 0
        self._pkgs = self._pkglst()
        self._build_pkginfo()
        if self.args['report'] == 'csv':
            self._gen_csv()
        elif self.args['report'] == 'json':
            self._gen_json()
        elif self.args['report'] == 'xml':
            self._gen_xml()

    def _pkglst(self):
        pkgs = []
        # Get the list of packages
        if self.args['reason'] != 'all':
            for p in sorted(self.yb.rpmdb.returnPackages()):
                if 'reason' not in p.yumdb_info:
                    continue
                reason = getattr(p.yumdb_info, 'reason')
                if reason == self.args['reason']:
                    pkgs.append(p)
        else:
            pkgs = sorted(self.yb.rpmdb.returnPackages())
        return(pkgs)

    def _build_pkginfo(self):
        for p in self._pkgs:
            _pkg = {'name': p.name,
                    'desc': p.summary,
                    'version': p.ver,
                    'release': p.release,
                    'arch': p.arch,
                    'built': datetime.datetime.fromtimestamp(p.buildtime),
                    'installed': datetime.datetime.fromtimestamp(p.installtime),
                    'repo': repo_re.sub('', p.ui_from_repo),
                    'sizerpm': p.packagesize,
                    'sizedisk': p.installedsize}
            self.pkgs.append(_pkg)

    def _gen_csv(self):
        if self.args['plain']:
            _fields = ['name']
        else:
            _fields = ['name', 'version', 'release', 'arch', 'desc', 'built',
                       'installed', 'repo', 'sizerpm', 'sizedisk']
        import csv
        if sys.hexversion >= 0x30000f0:
            _buf = io.StringIO()
        else:
            _buf = io.BytesIO()
        _csv = csv.writer(_buf, delimiter = self.args['sep_char'])
        if self.args['header']:
            if self.args['plain']:
                _csv.writerow(['Name'])
            else:
                _csv.writerow(['Name', 'Version', 'Release', 'Architecture', 'Description', 'Build Time',
                               'Install Time', 'Repository', 'Size (RPM)', 'Size (On-Disk)'])
        _csv = csv.DictWriter(_buf, fieldnames = _fields, extrasaction = 'ignore', delimiter = self.args['sep_char'])
        for p in self.pkgs:
            _csv.writerow(p)
        _buf.seek(0, 0)
        self.report = _buf.read()
        return()

    def _gen_json(self):
        import json
        if self.args['plain']:
            self.report = json.dumps([p['name'] for p in self.pkgs], indent = 4)
        else:
            self.report = json.dumps(self.pkgs, default = str, indent = 4)
        return()

    def _gen_xml(self):
        from lxml import etree
        _xml = etree.Element('packages')
        for p in self.pkgs:
            _attrib = copy.deepcopy(p)
            for i in ('built', 'installed', 'sizerpm', 'sizedisk'):
                _attrib[i] = str(_attrib[i])
            if self.args['plain']:
                _pkg = etree.Element('package', attrib = {'name': p['name']})
            else:
                _pkg = etree.Element('package', attrib = _attrib)
            _xml.append(_pkg)
            #del(_attrib['name'])  # I started to make it a more complex, nested structure... is that necessary?
        if self.args['header']:
            self.report = etree.tostring(_xml, pretty_print = True, xml_declaration = True, encoding = 'UTF-8')
        else:
            self.report = etree.tostring(_xml, pretty_print = True)
        return()


def parseArgs():
    args = argparse.ArgumentParser(description = ('This script lets you dump the list of installed packages'))
    args.add_argument('-p', '--plain',
                      dest = 'plain',
                      action = 'store_true',
                      help = 'If specified, only create a list of plain package names (i.e. don\'t include extra '
                             'information)')
    args.add_argument('-n', '--no-header',
                      dest = 'header',
                      action = 'store_false',
                      help = 'If specified, do not print column headers/XML headers')
    args.add_argument('-s', '--separator',
                      dest = 'sep_char',
                      default = ',',
                      help = 'The separator used to split fields in the output (default: ,) (only used for CSV '
                             'reports)')
    rprt = args.add_mutually_exclusive_group()
    rprt.add_argument('-c', '--csv',
                      dest = 'report',
                      default = 'csv',
                      action = 'store_const',
                      const = 'csv',
                      help = 'Generate CSV output (this is the default). See -n/--no-header, -s/--separator')
    rprt.add_argument('-x', '--xml',
                      dest = 'report',
                      default = 'csv',
                      action = 'store_const',
                      const = 'xml',
                      help = 'Generate XML output (requires the LXML module: yum install python-lxml)')
    rprt.add_argument('-j', '--json',
                      dest = 'report',
                      default = 'csv',
                      action = 'store_const',
                      const = 'json',
                      help = 'Generate JSON output')
    rsn = args.add_mutually_exclusive_group()
    rsn.add_argument('-a', '--all',
                     dest = 'reason',
                     default = 'all',
                     action = 'store_const',
                     const = 'all',
                     help = ('Parse/report all packages that are currently installed. '
                             'Conflicts with -u/--user and -d/--dep. '
                             'This is the default'))
    rsn.add_argument('-u', '--user',
                     dest = 'reason',
                     default = 'all',
                     action = 'store_const',
                     const = 'user',
                     help = ('Parse/report only packages which were explicitly installed. '
                             'Conflicts with -a/--all and -d/--dep'))
    rsn.add_argument('-d', '--dep',
                     dest = 'reason',
                     default = 'all',
                     action = 'store_const',
                     const = 'dep',
                     help = ('Parse/report only packages which were installed to satisfy a dependency. '
                             'Conflicts with -a/--all and -u/--user'))
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    p = PkgIndexer(**args)
    print(p.report)
    return()

if __name__ == '__main__':
    main()
