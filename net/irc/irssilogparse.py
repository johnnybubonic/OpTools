#!/usr/bin/env python3

import argparse
import os
import re
try:
    import magic
    has_magic = True
except ImportError:
    print(('Warning: you do not have the magic module installed ' +
           '(you can install it via "pip3 install --user python-magic"). ' +
           'Automatic log decompression will not work.'))
    has_magic = False

class logParser(object):
    def __init__(self, args, data = None):
        # We'll need these accessible across the entire class.
        self.args = args
        self.data = data
        self.bindata = data
        # This is a map to determine which module to use to decompress,
        # if we should.
        self.cmprsn_map = {'text/plain': None,  # Plain ol' text
                           'application/octet-stream': None,  # Sometimes the formatting with color gives this
                           'application/x-bzip2': 'bz2',  # Bzip2
                           'application/x-gzip': 'gzip',  # Gzip
                           'application/x-xz': 'lzma'}  # XZ
        # I though y'all liked GUIs.
        # ANSI, which is interpreted by the shell.
        # Only used if args['color'] = True
        self.ansi_prefix = '\e['
        # The hex prefex in the logs. We use this to either
        # convert to ANSI (hence the value for the key) or
        # to strip out coloring entirely.
        self.irssi_prefix = {'\x02': '1m',  # bold
                             '\x03': '0m'} # reset; prepare for color change
        # irssi to ANSI
        self.colormap = {''}
        # The full, interpreted path.
        if 'logfile' in self.args.keys():
            self.args['logfile'] = os.path.abspath(os.path.expanduser(self.args['logfile']))
        if not self.data:
            self.getLog()
        else:
            self.data = self.data.decode('utf-8').splitlines()
        # We're running as standalone or weren't called with a data buffer.
        if not isinstance(self.data, list):
            raise ValueError('Log data must be in list format.')
        self.decompress = None
        if has_magic:
            # Determine what decompressor to use, if we need to.
            _mime = magic.detect_from_content(self.bindata).mime_type
            self.decompress = self.cmprsn_map[_mime]
        if self.args['html'] and self.args['color']:
            try:
                import ansi2html
                has_html = True
            except ImportError:
                print(('Warning: you have selected HTML output but do not ' +
                       'have the ansi2html module installed. Rendering HTML ' +
                       'output is not possible.'))
                has_html = False
        else:
            has_html = False

    def getLog(self):
        if not os.path.isfile(self.args['logfile']):
            raise FileNotFoundError('{0} does not exist.'.formatself.args['logfile'])
        with open(self.args['logfile'], 'rb') as f:
            self.data = f.read().decode('utf-8').splitlines()
            f.seek(0, 0)
            self.bindata = f.read()
        return()

    def parseLog(self):
        if self.decompress:
            import importlib
            self.decmp = importlib.import_module(self.decompress)
            self.data = self.decmp.decompress(self.data)
        # TODO: format conversion/stripping
        if self.args['color']:
            _idx = 0
            for line in self.data[:]:
                for k, v in self.irssi_prefix.items():
                    _v = self.ansi_prefix + v
                    self.data[_idx] = re.sub(k, _v, line)
                _idx += 1
        return()

def parseArgs():
    args = argparse.ArgumentParser()
    args.add_argument('-c', '--color',
                      dest = 'color',
                      action = 'store_true',
                      help = ('Print the log with converted colors.'))
    args.add_argument('-H', '--html',
                      dest = 'html',
                      action = 'store_true',
                      help = ('Render HTML output.'))
    args.add_argument(dest = 'logfile',
                      metavar = 'path/to/logfile',
                      help = ('The path to the log file. It can be uncompressed ' +
                              'or compressed with XZ/LZMA, Gzip, or Bzip2.'))
    return(args)

if __name__ == '__main__':
    args = vars(parseArgs().parse_args())
    l = logParser(args)
    l.parseLog()
    #print(l.data.decode('utf-8'))
    print(''.join(l.data))
