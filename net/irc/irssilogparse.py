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
        self.has_html = False
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
        self.ansi_prefix = '\033['
        # irssi to ANSI
        self.colormap = {'00': '1;37m',  # White
                         '01': '0;30m',  # Black
                         '02': '0;34m',  # Blue
                         '03': '0;32m',  # Green
                         '04': '1;31m',  # Light Red
                         '05': '0;31m',  # Red
                         '06': '0;35m',  # Magenta (translated as Purple)
                         '07': '0;33m',  # Orange (translated as Brown)
                         '08': '1;33m',  # Yellow
                         '09': '1:32m',  # Light Green
                         '10': '0;36m',  # Cyan
                         '11': '1;36m',  # Light Cyan
                         '12': '1;34m',  # Light Blue
                         '13': '1;35m',  # Light Magenta (translated as Light Purple)
                         '14': '0;37m',  # Gray
                         '15': '1;37'}  # Light Gray (translated as White)
        # The full, interpreted path.
        if 'logfile' in self.args.keys():
            self.args['logfile'] = os.path.abspath(os.path.expanduser(self.args['logfile']))
        if not self.data:
            self.getLog()
        else:
            self.data = self.data.decode('utf-8').splitlines()
        self.decompress = None
        if has_magic:
            # Determine what decompressor to use, if we need to.
            _mime = magic.detect_from_content(self.data).mime_type
            self.decompress = self.cmprsn_map[_mime]
        if self.args['html']:
            try:
                import ansi2html
                self.has_html = True
            except ImportError:
                print(('Warning: you have selected HTML output but do not ' +
                       'have the ansi2html module installed. Rendering HTML ' +
                       'output is not possible.'))
                self.has_html = False
        else:
            self.has_html = False

    def getLog(self):
        if not os.path.isfile(self.args['logfile']):
            raise FileNotFoundError('{0} does not exist.'.formatself.args['logfile'])
        with open(self.args['logfile'], 'rb') as f:
            self.data = f.read()
        return()

    def parseLog(self):
        if self.decompress:
            import importlib
            self.decmp = importlib.import_module(self.decompress)
            self.data = self.decmp.decompress(self.data)
        if self.args['color']:
            _idx = 0
            _datalst = self.data.split(b'\n')
            for line in _datalst[:]:  # not really "lines", per se, but...
                # First we strip out some basic formatting at the beginning
                # of lines. Status lines are \x049/, chat lines are \x048/.
                # \x04g seem to be formatting resets of sort.
                line = re.sub('\x04[89]/'.encode('utf-8'),
                              ''.encode('utf-8'),
                              line)
                line = re.sub('\x04g'.encode('utf-8'),
                              ''.encode('utf-8'),
                              line)
                # Formatting resets
                line = re.sub('\x04e'.encode('utf-8'),
                              '\033[0m'.encode('utf-8'),
                              line)
                # Then we substitute bolds in. This is trickier, because
                # bolds (\x04c) *alternate*. So does the other? bold, \x02.
                for b in ('\x04c'.encode('utf-8'), '\x02'.encode('utf-8')):
                    _linelst = line.split(b)
                    _bold = False
                    _cnt = 0
                    for i in _linelst[:]:
                        if _bold:
                            _linelst[_cnt] = re.sub('^'.encode('utf-8'),
                                                    (self.ansi_prefix + '1m').encode('utf-8'),
                                                    i)
                        else:
                            _linelst[_cnt] = re.sub('^'.encode('utf-8'),
                                                    (self.ansi_prefix + '0m').encode('utf-8'),
                                                    i)
                        _cnt += 1
                        _bold = not _bold
                    line = b''.join(_linelst)
                # Then we handle colors.
                _cnt = 0
                _linelst = line.split(b'\x03')
                for i in _linelst[:]:
                    _color_idx = re.sub('^([0-9]{2}).*$'.encode('utf-8'),
                                        '\g<1>',
                                        i,
                                        re.MULTILINE).decode('utf-8')
                    if _color_idx in self.colormap.keys():
                        _linelst[_cnt] = re.sub('^[0-9]{2}'.encode('utf-8'),
                                                (self.ansi_prefix + self.colormap[_color_idx]).encode('utf-8'),
                                                i)
                    _cnt += 1
                line = b''.join(_linelst)
                # Lastly, we fix join/part and other messages.
                _cnt = 0
                _linelst = line.split(b'\x04;/')
                for i in _linelst[:]:
                    _templine = re.sub('^'.encode('utf-8'),
                                        ''.encode('utf-8'),
                                        i,
                                        re.MULTILINE)
                    _templine = re.sub('-!-'.encode('utf-8'),
                                       '\033[2m-!-'.encode('utf-8'),
                                       _templine)
                    _linelst[_cnt] = re.sub('\x043/'.encode('utf-8'),
                                            ''.encode('utf-8'),
                                            _templine)
                    _cnt += 1
                line = re.sub(b'^\x1b\[0;32m\x1b\[0m\x1b\[0m', b'\033[0m', b''.join(_linelst))
                # Lastly we strip out \x04>/
                line = re.sub(b'\x04>/', b'', line)
                ###
                _datalst[_idx] = line
                _idx += 1
                ###
            self.data = b'\n'.join(_datalst)
            if self.args['html']:
                try:
                    import ansi2html
                    _has_html = True
                except ImportError:
                    print(('Warning: you have selected HTML output but do not ' +
                           'have the ansi2html module installed. Rendering HTML ' +
                           'output is not possible.'))
                    _has_html = False
            else:
                _has_html = False
            if _has_html:
                # This... basically sucks. It currently doesn't properly interpret the ANSI.
                _html = ansi2html.Ansi2HTMLConverter()
                self.data = _html.convert(self.data.decode('utf-8'))
        else:  # We want plaintext, so strip ALL formatting.
            _stripbytes = ['\x04>/', '\x02', '\x043/', '\x048/', '\x049/', '\x04g', '\x04e', '\x04c', '\x04;/']
            for b in _stripbytes:
                self.data = re.sub(b.encode('utf-8'), ''.encode('utf-8'), self.data)
            self.data = re.sub('\\x03[0-9]{2}'.encode('utf-8'), ''.encode('utf-8'), self.data)
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
    print(l.data.decode('utf-8'))