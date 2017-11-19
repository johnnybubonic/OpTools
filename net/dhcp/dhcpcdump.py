#!/usr/bin/env python3

# See RFC 2131, Figure 1 and Table 1 (section 2)
# Much thanks to https://github.com/igordcard/dhcplease for digging into dhcpcd
# source for the actual file structure (and providing inspiration).

import argparse
import collections
import os
import re
import struct
from io import BytesIO

## DEFINE SOME PRETTY STUFF ##
class color(object):
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class packetParser(object):
    def __init__(self, data):
        ## Set the segment labels and struct formats
        self.fmt = collections.OrderedDict()
        # In the below, 'cnt' is how large (in octets) the field is.
        # 'fmt' is a struct format string (https://docs.python.org/3/library/struct.html#format-characters)
        # "op" through "hops" (incl.) may actually be '8B' instead of '8c'.
        self.fmt['op'] = {'cnt': 8, 'fmt': '8c'}  # this will always be \x02
        self.fmt['htype'] = {'cnt': 8, 'fmt': '8c'}  # this will always be \x01
        self.fmt['hlen'] = {'cnt': 8, 'fmt': '8c'}
        self.fmt['hops'] = {'cnt': 8, 'fmt': '8c'}
        self.fmt['xid'] = {'cnt': 32, 'fmt': '8I'}
        self.fmt['secs'] = {'cnt': 16, 'fmt': '8H'}
        self.fmt['flags'] = {'cnt': 16, 'fmt': '8H'}
        # "ciaddr" through "giaddr" (incl.) may actually be '4c' instead of '4B'.
        self.fmt['ciaddr'] = {'cnt': 4, 'fmt': '4B'}
        self.fmt['yiaddr'] = {'cnt': 4, 'fmt': '4B'}
        self.fmt['siaddr'] = {'cnt': 4, 'fmt': '4B'}
        self.fmt['giaddr'] = {'cnt': 4, 'fmt': '4B'}
        # "chaddr" through "file" (incl.) may actually be <#>c instead of <#>B.
        self.fmt['chaddr'] = {'cnt': 16, 'fmt': '16B'}  # first 6 bytes used for MAC addr of client
        self.fmt['sname'] = {'cnt': 64, 'fmt': '64B'}  # server host name (via BOOTP)
        self.fmt['file'] = {'cnt': 128, 'fmt': '128B'}  # the boot filename (for BOOTP)
        # OPTIONS - RFC 2132
        # Starting at octet 320 (so, f.seek(319, 0)) to the end of the message are
        # DHCP options. It's a variable-length field so it makes things tricky
        # for us. But it's at *least* 312 octets long per the RFC?
        # It probably starts with a magic.
        #self.dhcp_opts = {'idx': 324, 'cnt': 4, 'fmt': '4c'}
        #self.dhcp_opts = {'idx': 324, 'cnt': 4, 'fmt': None}
        self.opts = {'magic': b'\x63\x82\x53\x63',
                     'struct': {'idx': 324, 'cnt': 4, 'fmt': '4B'},
                     'size': 0,
                     'bytes': b'\00'}
        ## Convert the data into a bytes object because struct.unpack() wants a stream
        self.buf = BytesIO(data)

    def getStd(self):
        self.reconstructed_segments = collections.OrderedDict()
        _idx = 0  # add to this with the 'cnt' value for each iteration.
        for k in self.fmt.keys():
            print('Segment: ' + k)  # TODO: remove, this stuff goes in the printer
            pkt = struct.Struct(self.fmt[k]['fmt'])
            self.buf.seek(_idx, 0)
            try:
                self.reconstructed_segments[k] = pkt.unpack(self.buf.read(self.fmt[k]['cnt']))
            except struct.error as e:
                # Some DHCP implementations are... broken.
                # I've noticed it mostly in Verizon Fi-OS gateways/WAPs/routers.
                print('Warning({0}): {1}'.format(k, e))
                self.buf.seek(_idx, 0)
                _truesize = len(self.buf.read(self.fmt[k]['cnt']))
                print('Length of bytes read: {0}'.format(_truesize))
                # But sometimes it's... kind of fixable?
                if k == 'file' and _truesize < self.fmt[k]['cnt']:
                    self.buf.seek(_idx, 0)
                    self.fmt[k] = {'cnt': _truesize, 'fmt': '{0}B'.format(_truesize)}
                    pkt = struct.Struct(self.fmt[k]['fmt'])
                    print('Struct format size automatically adjusted.')
                    try:
                        self.reconstructed_segments[k] = pkt.unpack(self.buf.read(self.fmt[k]['cnt']))
                    except struct.error as e2:
                        # yolo.
                        print('We still couldn\'t populate {0}; filling with a nullbyte.'.format(k))
                        print('Error (try #2): {0}'.format(e2))
                        print('We read {0} bytes.'.format(_truesize))
                        print('fmt: {0}'.format(self.fmt[k]['fmt']))
                        self.reconstructed_segments[k] = b'\00'
            _idx += self.fmt[k]['cnt']
            self.buf.seek(_idx, 0)
            # Finally, check for opts. If they exist, populate.
            _optbytes = len(self.buf.read())
            if _optbytes >= 1:
                self.opts['size'] = _optbytes
                self.buf.seek(_idx, 0)
                self.opts['bytes'] = self.buf.read()  # read to the end
        return()

    def getOpts(self):
        pass

    def close(self):
        self.buf.close()

def parseArgs():
    args = argparse.ArgumentParser()
    _deflease = '/var/lib/dhcpcd/'
    args.add_argument('-l', '--lease',
                      metavar = '/path/to/lease/dir/or_file.lease',
                      default = _deflease,
                      dest = 'leasepath',
                      help = ('The path to the directory of lease files or specific lease file. ' +
                              'If a directory is provided, all lease files found within will be ' +
                              'parsed. Default: {0}{1}{2}').format(color.BOLD,
                                                                   _deflease,
                                                                   color.END))
    args.add_argument('-n', '--no-color',
                      action = 'store_false',
                      dest = 'color',
                      help = ('If specified, suppress color formatting in output.'))
    args.add_argument('-d', '--dump',
                      metavar = '/path/to/dumpdir',
                      default = False,
                      dest = 'dump',
                      help = ('If provided, dump the parsed leases to this directory (in ' +
                              'addition to printing). It will dump with the same filename ' +
                              'and overwrite any existing file with the same filename, so ' +
                              'do NOT use the same directory as your dhcpcd lease files! ' +
                              '({0}-l/--lease{1}). The directory will be created if it does ' +
                              'not exist').format(color.BOLD,
                                                  color.END))
    args.add_argument('-p', '--pretty',
                      action = 'store_true',
                      dest = 'prettyprint',
                      help = ('If specified, include color formatting {0}in the dump ' +
                              'file(s){1}').format(color.BOLD, color.END))
    return(args)

def getLeaseData(fpath):
    if not os.path.isfile(fpath):
        raise FileNotFoundError('{0} does not exist'.format(fpath))
    with open(fpath, 'rb') as f:
        _data = f.read()
    return(_data)

def iterLease(args):
    # If the lease path is a file, just operate on that.
    # If it's a directory, iterate (recursively) through it.
    leases = {}
    if not os.path.lexists(args['leasepath']):
        raise FileNotFoundError('{0} does not exist'.format(args['leasepath']))
    if os.path.isfile(args['leasepath']):
        _pp = packetParser(getLeaseData(args['leasepath']))
        # TODO: convert the hex vals to their actual vals... maybe?
        _keyname = re.sub('^(dhcpcd-)?(.*)\.lease$',
                          '\g<2>',
                          os.path.basename(args['leasepath']))
        leases[_keyname] = leaseParse(_pp, args)
    else:
        # walk() instead of listdir() because whotf knows when some distro like
        # *coughcoughUbuntucoughcough* will do some breaking change like creating
        # subdirs based on iface name or something.
        for _, _, files in os.walk(args['leasepath']):
            if not files:
                continue
            files = [i for i in files if i.endswith('.lease')]  # only get .lease files
            for i in files:
                _args = args.copy()
                _fpath = os.path.join(args['leasepath'], i)
                _keyname = re.sub('^(dhcpcd-)?(.*)\.lease$', '\g<2>', os.path.basename(_fpath))
                _dupeid = 0
                # JUST in case there are multiple levels of dirs in the future
                # that have files of the sama name
                while _keyname in leases.keys():
                    # TODO: convert the hex vals to their actual vals... maybe?
                    _keyname = re.sub('^$',
                                      '\g<1>.{0}'.format(_dupeid),
                                      _keyname)
                    _dupeid += 1
                _pp = packetParser(getLeaseData(_fpath))
                leases[_keyname] = leaseParse(_pp, _args, fname = _fpath)
    return(leases)

def leaseParse(pp, args, fname = False):
    # Essentially just a wrapper function.
    # Debugging output...
    if fname:
        print(fname)
    pp.getStd()
    pp.getOpts()
    if args['dump']:
        pass  # TODO: write to files, creating dump dir if needed, etc.
    pp.close()
    # do pretty-printing (color-coded segments, etc.) here
    return(pp.reconstructed_segments)

if __name__ == '__main__':
    args = vars(parseArgs().parse_args())
    args['leasepath'] = os.path.abspath(os.path.expanduser(args['leasepath']))
    if not os.path.lexists(args['leasepath']):
        exit('{0} does not exist!'.format(args['leasepath']))
    leases = iterLease(args)
    # just print for now until we write the parser/prettyprinter
    print(list(leases.keys()))
