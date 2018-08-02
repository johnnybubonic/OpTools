#!/usr/bin/env python3

## REFERENCE ##
# https://github.com/myano/jenni/wiki/IRC-String-Formatting
# https://www.mirc.com/colors.html
# https://en.wikipedia.org/wiki/ANSI_escape_code
# https://github.com/shabble/irssi-docs/wiki/Formats#Colourising-Text-in-IRC-Messages


import argparse
import curses
import os
import pprint
import re
import sys
try:
    import magic
    has_magic = True
except ImportError:
    print('Warning: you do not have the magic module installed (you can '
          'install it via "pip3 install --user file-magic"). Automatic log '
          'decompression will not work.')
    has_magic = False

# This is a map to determine which module to use to decompress,
# if we should.
cmprsn_map = {'text/plain': None,  # Plain ol' text
              # Sometimes the formatting with color gives this
              'application/octet-stream': None,
              'application/x-bzip2': 'bz2',  # Bzip2
              'application/x-gzip': 'gzip',  # Gzip
              'application/x-xz': 'lzma'}  # XZ

# irssi/mIRC to ANSI
# Split into 3 maps (truecolor will be populated later, currently uses 8-bit):
# - 8 (3/4 bit color values, 8 colors)
# - 256 (8-bit, 256 colors)
# - 'truecolor' (24-bit, ISO-8613-3, 16777216 colors)
# Keys are the mIRC color value
# Values are:
# - 8: tuple for ANSI fg and bg values
# - 256: single value (same number is used for fg and bg)
# - 'truecolor': tuple of (R#, G#, B#) (same number is used for fg and bg)
# In addition, all three have the following:
# - ansi_wrap: the string formatter.
#              fg: foreground color
#              bg: background color (if present)
#    They are concatted together in that order.
            ## https://en.wikipedia.org/wiki/ANSI_escape_code#3/4_bit
colormap = {8: {'0': ('97', '107'),
                '1': ('30', '40'),
                '2': ('34', '44'),
                '3': ('32', '42'),
                '4': ('91', '101'),
                '5': ('31', '41'),
                '6': ('35', '45'),
                '7': ('33', '43'),
                '8': ('93', '103'),
                '9': ('92', '102'),
                '10': ('36', '46'),
                '11': ('96', '106'),
                '12': ('94', '104'),
                '13': ('95', '105'),
                '14': ('90', '100'),
                '15': ('37', '47'),
                'ansi_wrap': {'fg': '\x1b[{0}',
                              'bg': ';{0}m'}},
            ## https://en.wikipedia.org/wiki/ANSI_escape_code#8-bit
            256: {'0': '15',
                  '1': '0',
                  '2': '19',
                  '3': '34',
                  '4': '196',
                  '5': '52',
                  '6': '90',
                  '7': '208',
                  '8': '226',
                  '9': '82',
                  '10': '37',
                  '11': '51',
                  '12': '21',
                  '13': '199',
                  '14': '241',
                  '15': '252',
                  'ansi_wrap': {'fg': '\x1b[38;5;{0}m',
                                'bg': '\x1b[48;5;{0}m'}},
            ## https://en.wikipedia.org/wiki/ANSI_escape_code#24-bit
            # (can just use mIRC's R,G,B)
            'truecolor': {'0': ('255', '255', '255'),
                          '1': ('0', '0', '0'),
                          '2': ('0', '0', '127'),
                          '3': ('0', '147', '0'),
                          '4': ('255', '0', '0'),
                          '5': ('127', '0', '0'),
                          '6': ('156', '0', '156'),
                          '7': ('252', '127', '0'),
                          '8': ('255', '255', '0'),
                          '9': ('0', '252', '0'),
                          '10': ('0', '147', '147'),
                          '11': ('0', '255', '255'),
                          '12': ('0', '0', '252'),
                          '13': ('255', '0', '255'),
                          '14': ('127', '127', '127'),
                          '15': ('210', '210', '210'),
                          'ansi_wrap': {'fg': '\x1b[38;2;{0[0]},{0[1]},{0[2]}',
                                        'bg': '\x1b[48;2;{0[0]},'
                                              '{0[1]},{0[2]}'}}}

def get_palette():
    # Return 8, 256, or 'truecolor'
    colorterm = os.getenv('COLORTERM', None)
    if colorterm == 'truecolor':
        # TODO: 24-bit support (16777216 colors) instead of 8-bit.
        # See note above.
        #return('truecolor')
        return(256)
    else:
        curses.initscr()
        curses.start_color()
        c = curses.COLORS
        curses.endwin()
        return(c)

def color_converter(data_in, palette_map):
    # Only used if logParser().args['color'] = True
    # Convert mIRC/Irssi color coding to ANSI color codes.
    color_ptrn = re.compile('\x03[0-9]{1,2}(,[0-9]{1,2})?')
    _colors = colormap[palette_map]
    # the value to reset formatting to the terminal default
    reset_char = '\x1b[0m'
    # the value to reset the foreground text
    def_fg = '\x1b[39m'
    # the value to reset the background text
    def_bg = '\x1b[49m'
    regex = {'nick': re.compile('\x04[89]/'),
             'bold': re.compile('\x02'),
             ## Doublecheck this. what is the significance of \x04(.*) chars?
             'reset': re.compile('\x04(g|c|[389;]/?|e|>)?/?'),
             'color_clear': re.compile('\x0f(g|c|[389;]/?|e)?/?')}
    # A sub-function that generates the replacement characters.
    def _repl(ch_in):
        _ch = ch_in.group().lstrip('\x03')
        _chars = [i.strip() for i in _ch.split(',', 1)]
        if len(_chars) == 1:
            ch_out = _colors['ansi_wrap']['fg'].format(_chars[0])
        elif len(_chars) == 2:
            ch_out = (_colors['ansi_wrap']['fg'].format(_chars[0]) +
                      _colors['ansi_wrap']['bg'].format(_chars[1]))
        else:
            raise RuntimeError('Parsing error! "{0}"'.format(ch_in))
        return(ch_out)
    data = data_in.splitlines()
    for idx, line in enumerate(data[:]):
        # Get some preliminary replacements out of the way.
        line = regex['nick'].sub(' ', line, 1)
        line = regex['reset'].sub(reset_char, line)
        line = regex['color_clear'].sub(def_fg + def_bg, line)
        # TODO: use ptrn.sub(_repl, line) instead since that works and
        # this does not
        # First set is text color
        # Second set, if present, is bg color
        line = color_ptrn.sub(_repl, line)
        data[idx] = line
    return('\n'.join(data))

def plain_stripper(data_in):
    # Strip to plaintext only.
    data = data_in.splitlines()
    ptrns = [re.compile('\x04(g|c|[389;]/?|e|>)/?'),
             re.compile('((\x03)\d\d?,\d\d?|(\x03)\d\d?|[\x01-\x1F])')]
    for idx, line in enumerate(data[:]):
        # This cleans the nick field
        l = re.sub('\x04[89]/', ' ', line, 1)
        # And these clean the actual chat messages
        for p in ptrns:
            l = p.sub('', l)
        data[idx] = l
    return('\n'.join(data))

class irssiLogParser(object):
    def __init__(self, args, data = None):
        # We'll need these accessible across the entire class.
        self.args = args
        # If specified, self.data takes precedence over self.args['logfile']
        # (if it was specified).
        self.data = data
        self.raw = data
        self.has_html = False
        self.decompress = None
        if 'color' in self.args and self.args['color']:
            if not self.args['html']:
                # Ensure that we support color output.
                curses.initscr()
                self.args['color'] = curses.can_change_color()
                curses.endwin()
                if not self.args['color'] and not self.args['raw']:
                    raise RuntimeError('You have specified ANSI colorized '
                                       'output but your terminal does not '
                                       'support it. Use -fc/--force-color '
                                       'to force.')
                elif not self.args['color'] and self.args['raw']:
                    self.args['color'] = True  # Force the output anyways.
        if self.args['color']:
            if not self.args['raw']:
                self.colors = get_palette()
            else:
                self.colors = 8  # Best play it safe for maximum compatibility.
        # The full, interpreted path.
        if ('logfile' in self.args.keys() and
            self.args['logfile'] is not None):
            self.args['logfile'] = os.path.abspath(
                                        os.path.expanduser(
                                                self.args['logfile']))
        if not self.data:
            self.getlog()
        else:
            # Conform everything to bytes.
            if not isinstance(self.data, bytes):
                self.data = self.data.encode('utf-8')
        self.decompressor()
        self.parser()

    def getlog(self):
        # A filepath was specified
        if self.args['logfile']:
            if not os.path.isfile(self.args['logfile']):
                raise FileNotFoundError('{0} does not exist'.format(
                                                        self.args['logfile']))
            with open(self.args['logfile'], 'rb') as f:
                self.data = f.read()
        # Try to get it from stdin
        else:
            if not sys.stdin.isatty():
                self.data = sys.stdin.buffer.read()
            else:
                raise ValueError('Either a path to a logfile must be '
                                 'specified or you must pipe a log in from '
                                 'stdin.')
        self.raw = self.data
        return()

    def decompressor(self):
        # TODO: use mime module as fallback?
        # https://docs.python.org/3/library/mimetypes.html
        # VERY less-than-ideal since it won't work without self.args['logfile']
        # (and has iffy detection at best, since it relies on file extensions).
        # Determine what decompressor to use, if we need to.
        if has_magic:
            _mime = magic.detect_from_content(self.data).mime_type
            self.decompress = cmprsn_map[_mime]
            if self.decompress:
                import importlib
                decmp = importlib.import_module(self.decompress)
                self.raw = decmp.decompress(self.data)
        else:
            # Assume that it's text and that it isn't compressed.
            # We'll get a UnicodeDecodeError exception if it isn't.
            pass
        try:
            self.raw = self.data.decode('utf-8')
        except UnicodeDecodeError:
            pass
        self.data = self.raw
        return()

    def parser(self):
        if 'color' not in self.args or not self.args['color']:
            self.data = plain_stripper(self.data)
        else:
            self.data = color_converter(self.data, self.colors)
        # Just in case...
        self.data += '\x1b[0m'
        return()

def parseArgs():
    args = argparse.ArgumentParser()
    args.add_argument('-c', '--color',
                      dest = 'color',
                      action = 'store_true',
                      help = ('Print the log with converted colors (ANSI)'))
    args.add_argument('-r', '--raw',
                      dest = 'raw',
                      action = 'store_true',
                      help = ('Use this switch if your terminal is detected '
                              'as not supporting color output but wish to '
                              'force it anyways. A string representation of '
                              'the ANSI output will be produced instead ('
                              'suitable for pasting elsewhere). Only used if '
                              '-c/--color is enabled (ignored with '
                              '-H/--html)'))
    args.add_argument('-H', '--html',
                      dest = 'html',
                      action = 'store_true',
                      help = ('Render HTML output'))
    args.add_argument(dest = 'logfile',
                      default = None,
                      nargs = '?',
                      metavar = 'path/to/logfile',
                      help = ('The path to the log file. It can be uncompressed ' +
                              'or compressed with XZ/LZMA, Gzip, or Bzip2. '
                              'If not specified, read from stdin'))
    return(args)

if __name__ == '__main__':
    args = vars(parseArgs().parse_args())
    l = irssiLogParser(args)
    import shutil
    cols = shutil.get_terminal_size().columns
    #pprint.pprint(l.args, width = cols)
    pprint.pprint(l.raw, width = cols)
    with open('/tmp/freenode.formatted', 'r') as f:
        print(f.read())
    #pprint.pprint(l.data, width = cols)
    #pprint.pprint(repr(l.data).split('\\n'))
    print(l.data)
    # l.parseLog()
    # print(l.data.decode('utf-8'))
