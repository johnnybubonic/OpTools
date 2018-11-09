#!/usr/bin/env python3

import argparse
import copy
import datetime
import os
import pathlib
import re
import sys
import lxml.etree


# Serialize BSD mtree spec files into XML.
# On arch, BSD mtree is ported in the AUR as nmtree.

# TODO: use bitwise operations to convert octal modes back and forth. ex. at https://stackoverflow.com/a/1746850

class MtreeXML(object):
    def __init__(self, spec):
        # spec is a string or bytes
        if not isinstance(spec, (str, bytes)):
            raise ValueError('spec must be a raw string of the spec or a bytes object of the string')
        if isinstance(spec, bytes):
            try:
                spec = spec.decode('utf-8')
            except UnicodeDecodeError:
                raise ValueError('spec must be a utf-8 encoded set of bytes if using byte mode')
        self._strptime_fmt = '%a %b %d %H:%M:%S %Y'
        self.orig_spec = copy.deepcopy(spec)  # For referencing in case someone wanted to write it out.
        # We NOW need to handle the escaped linebreaking it does.
        self._specdata = re.sub('\\\\\s+', '', spec).splitlines()
        self._get_header()
        self._spec = {'header': self._header,
                      'paths': {}}
        # Template for an item.
        # Default keywords are:
        # flags, gid, link, mode, nlink, size, time, type, uid
        self._tplitem = {
            'type': None,  # ('block', 'char', 'dir', 'fifo', 'file', 'link', 'socket')
            # checksum of file (if it's a file) (int)
            # On all *nix platforms, the cksum(1) utility (which is what the mtree spec uses) follows
            # the POSIX standard CRC (which is NOT CRC-1/CRC-16 nor CRC32!):
            # http://pubs.opengroup.org/onlinepubs/009695299/utilities/cksum.html
            # For a python implementation,
            # https://stackoverflow.com/questions/6835381/python-equivalent-of-unix-cksum-function
            # See also crcmod (in PyPi).
            'cksum': None,
            # "The device number to use for block or char file types." Should be converted to a tuple of one
            #  of the following:
            # - (format(str), major(int), minor(int))
            # - (format(str), major(int), unit(str?), subunit(str?)) (only used on bsdos formats)
            # - (number(int?), ) ("opaque" number)
            # Valid formats are, per man page of mtree:
            # native, 386bsd, 4bsd, bsdos, freebsd, hpux, isc, linux, netbsd, osf1, sco, solaris, sunos,
            # svr3, svr4, ultrix
            'device': None,
            # File flags as symbolic name. BSD-specific thing? TODO: testing on BSD system
            'flags': [],
            'ignore': False,  # An mtree-internal flag to ignore hierarchy under this item
            'gid': None,  # The group ID (int)
            'gname': None,  # The group name (str)
            'link': None,  # The link target/source, if a link.
            # The MD5 checksum digest (str? hex?). "md5digest" is a synonym for this, so it's consolidated in
            # as the same keyword.
            'md5': None,
            # The mode (in octal) (we convert it to a python-native int for os.chmod/stat, etc.)
            # May also be a symbolic value; TODO: map symbolic to octal/int.
            'mode': None,
            'nlink': None,  # Number of hard links for this item.
            'optional': False,  # This item may or may not be present in the compared directory for checking.
            'rmd160': None,  # The RMD-160 checksum of the file. "rmd160digest" is a synonym.
            'sha1': None,  # The SHA-1 sum. "sha1digest" is a synonym.
            'sha256': None,  # SHA-2 256-bit checksum; "sha256digest" is a synonym.
            'sha384': None,  # SHA-2 384-bit checksum; "sha384digest" is a synonym.
            'sha512': None,  # SHA-2 512-bit checksum; "sha512digest" is a synonym.
            'size': None,  # Size of the file in bytes (int).
            'tags': [],  # mtree-internal tags (comma-separated in the mtree spec).
            'time': None,  # Time the file was last modified (in Epoch fmt as float).
            'uid': None,  # File owner UID (int)
            'uname': None  # File owner username (str)
            # And lastly, "children" is where the children files/directories go. We don't include it in the template;
            # it's added programmatically.
            # 'children': {}
            }
        # Global aspects are handled by "/set" directives.
        # They are restored by an "/unset". Since they're global and stateful, they're handled as a class attribute.
        self._settings = copy.deepcopy(self._tplitem)
        self._parse_items()
        del(self._settings, self._tplitem, self._strptime_fmt, self._specdata)


    def _get_header(self):
        self._header = {}
        _headre = re.compile('^#\s+(user|machine|tree|date):\s')
        _cmtre = re.compile('^\s*#\s*')
        _blklnre = re.compile('^\s*$')
        for idx, line in enumerate(self._specdata):
            if _headre.search(line):  # We found a header item.
                l = [i.lstrip() for i in _cmtre.sub('', line).split(':', 1)]
                header = l[0]
                val = (l[1] if l[1] is not '(null)' else None)
                if header == 'date':
                    val = datetime.datetime.strptime(val, self._strptime_fmt)
                elif header == 'tree':
                    val = pathlib.PosixPath(val)
                self._header[header] = val
            elif _blklnre.search(line):
                break  # We've reached the end of the header. Otherwise...
            else:  # We definitely shouldn't be here, but this means the spec doesn't even have a header.
                break
        return()

    def _parse_items(self):
        # A pattern (compiled for performance) to match commands.
        _stngsre = re.compile('^/(un)?set\s')
        # Per the man page:
        # "Empty lines and lines whose first non-whitespace character is a hash mark (‘#’) are ignored."
        _ignre = re.compile('^(\s*(#.*)?)?$')
        # The following regex is used to quickly and efficiently check for a synonymized hash name.
        _hashre = re.compile('^(md5|rmd160|sha1|sha256|sha384|sha512)(digest)?$')
        # The following regex is to test if we need to traverse upwards in the path.
        _parentre = re.compile('^\.{,2}/?$')
        # _curpath = self.header['tree']
        _curpath = pathlib.PosixPath('/')
        _types = ('block', 'char', 'dir', 'fifo', 'file', 'link', 'socket')
        # This parses keywords. Used by both item specs and /set.
        def _kwparse(kwline):
            out = {}
            for i in kwline:
                l = i.split('=', 1)
                if len(l) < 2:
                    l.append(None)
                k, v = l
                if v == 'none':
                    v = None
                # These are represented as octals.
                if k in ('mode', ):
                    # TODO: handle symbolic references too (e.g. rwxrwxrwx)
                    if v.isdigit():
                        v = int(v, 8)  # Convert from the octal. This can then be used directly with os.chmod etc.
                # These are represented as ints
                elif k in ('uid', 'gid', 'cksum', 'nlink'):
                    if v.isdigit():
                        v = int(v)
                # These are booleans (represented as True by their presence).
                elif k in ('ignore', 'optional'):
                    v = True
                # These are lists (comma-separated).
                elif k in ('flags', 'tags'):
                    if v:
                        v = [i.strip() for i in v.split(',')]
                # The following are synonyms.
                elif _hashre.search(k):
                    k = _hashre.sub('\g<1>', k)
                elif k == 'time':
                    v = datetime.datetime.fromtimestamp(float(v))
                elif k == 'type':
                    if v not in _types:
                        raise ValueError('{0} not one of: {1}'.format(v, ', '.join(_types)))
                out[k] = v
            return(out)
        def _unset_parse(unsetline):
            out = {}
            if unsetline[1] == 'all':
                return(copy.deepcopy(self._tplitem))
            for i in unsetline:
                out[i] = self._tplitem[i]
            return(out)
        # The Business-End (TM)
        for idx, line in enumerate(self._specdata):
            _fname = copy.deepcopy(_curpath)
            # Skip these lines
            if _ignre.search(line):
                continue
            l = line.split()
            if _parentre.search(line):
                _curpath = _curpath.parent
            elif not _stngsre.search(line):
                # So it's an item, not a command.
                _itemsettings = copy.deepcopy(self._settings)
                _itemsettings.update(_kwparse(l[1:]))
                if _itemsettings['type'] == 'dir':
                    # SOMEONE PLEASE let me know if there's a cleaner way to do this.
                    _curpath = pathlib.PosixPath(os.path.normpath(_curpath.joinpath(l[0])))
                    _fname = _curpath
                else:
                    _fname = pathlib.PosixPath(os.path.normpath(_curpath.joinpath(l[0])))
                self._spec['paths'][_fname] = _itemsettings
            else:
                # It's a command. We can safely split on whitespace since the man page specifies the
                # values are not to contain whitespace.
                # /set
                if l[0] == '/set':
                    del(l[0])
                    self._settings.update(_kwparse(l))
                # /unset
                else:
                    self._settings.update(_unset_parse(l))
                continue
        return()

    def convert(self, architecture = 'shallow'):
        # If architecture is 'shallow', create the following structure:
        # <mtree ...>
        #   <item path='/path/to/item' keyword1='kw1_value' ... />
        #   <item path='/path/to/another/item' keyword1='kw2_value' ... />
        # </mtree>
        # If 'deep',
        # <mtree ...>
        #   <item>
        #     <path>/path/to/item</path>
        #     <keyword1>kw1_value</keyword1>
        #     ...
        #   </item>
        #   <item>
        #     <path>/path/to/another/item</path>
        #     <keyword1>kw2_value</keyword1>
        #    </item>
        # </mtree>
        if architecture not in ('shallow', 'deep'):
            raise ValueError('The architecture specified is not valid.')
        # TODO: create XSD
        # _ns = {
        #     None: 'http://mtreexml.square-r00t.net/',
        #     'xsi': 'http://www.w3.org/2001/XMLSchema-instance'}
        # _xsi = {
        #     '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation': 'http://mtreexml.square-r00t.net mtree.xsd'}
        #self.cfg = lxml.etree.Element('mtree', nsmap = _ns, attrib = _xsi)
        self.xml = lxml.etree.Element('mtree')
        # Add the header(s)
        for k in self._header:
            if not isinstance(self._header[k], str):
                self._header[k] = str(self._header[k])
            self.xml.attrib[k] = copy.deepcopy(self._header[k])
        # We use this compiled regex to format octals into string representations.
        _octre = re.compile('^0o')
        # Now add the paths.
        for path in self._spec['paths']:
            p = lxml.etree.Element('item')
            if architecture == 'deep':
                e = lxml.etree.Element('path')
                e.text = str(path)
                p.append(e)
            for k in self._spec['paths'][path]:
                # None attributes
                if not self._spec['paths'][path][k]:
                    continue
                # Bools
                if isinstance(self._spec['paths'][path][k], bool):
                    if architecture == 'shallow':
                        self._spec['paths'][path][k] = str(self._spec['paths'][path][k]).lower()
                    elif architecture == 'deep':
                        e = lxml.etree.Element(k)
                        e.attrib['enabled'] = str(self._spec['paths'][path][k]).lower()
                        p.append(e)
                        continue
                # Modes are stored in int, so we need a string repr of octal.
                if k == 'mode':
                    self._spec['paths'][path][k] = '{0:0>4}'.format(_octre.sub('',
                                                                               str(oct(self._spec['paths'][path][k]))))
                if not isinstance(self._spec['paths'][path][k], str):
                    self._spec['paths'][path][k] = str(self._spec['paths'][path][k])
                if architecture == 'shallow':
                    if 'path' not in p.attrib:
                        p.attrib['path'] = str(path)
                    p.attrib[k] = self._spec['paths'][path][k]
                elif architecture == 'deep':
                    e = lxml.etree.Element(k)
                    e.text = self._spec['paths'][path][k]
                    p.append(e)
            self.xml.append(p)
        self.xml_str = lxml.etree.tostring(self.xml,
                                           encoding = 'utf-8',
                                           xml_declaration = True,
                                           pretty_print = True).decode('utf-8')
        return()

def parseArgs():
    args = argparse.ArgumentParser(description = 'Parse BSD-style mtree specs into XML.')
    xmlarch = args.add_mutually_exclusive_group()
    xmlarch.add_argument('-s', '--shallow',
                         dest = 'architecture',
                         action = 'store_const',
                         const = 'shallow',
                         default = 'shallow',
                         help = 'If specified, create a "shallow" XML structure (default) (conflicts with -d/--deep)')
    xmlarch.add_argument('-d', '--deep',
                         dest = 'architecture',
                         action = 'store_const',
                         const = 'deep',
                         default = 'shallow',
                         help = 'If specified, create a "deep" XML structure (conflicts with -s/--shallow)')
    args.add_argument('specfile',
                      nargs = '?',
                      help = ('The path to the mtree spec file. Ignored if data is piped to stdin'))
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    stdin = None
    if not sys.stdin.isatty():
        stdin = sys.sdtin.buffer.read()
    if stdin:
        args['spec'] = stdin
    else:
        if not args['specfile']:
            raise argparse.ArgumentError(None, 'You must specify a specfile if you are not piping in one!')
        args['specfile'] = os.path.abspath(os.path.expanduser(args['specfile']))
        with open(args['specfile'], 'r') as f:
            args['spec'] = f.read()
    mtree = MtreeXML(args['spec'])
    mtree.convert(args['architecture'])
    print(mtree.xml_str)

if __name__ == '__main__':
    main()
