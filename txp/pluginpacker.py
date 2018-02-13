#!/usr/bin/env python3

# TODO / INCOMPLETE
# reference: https://github.com/Bloke/ied_plugin_composer/blob/master/ied_plugin_composer.php

import argparse
import base64
import gzip
import os
import sys

class pluginParse(object):
    def __init__(self, plugindata):
        # fear my list comprehensions! FEAR THEM.
        self.data = '\n'.join([i for i in plugindata.decode('utf-8').splitlines() if not i.strip().startswith('#') and i != ''])
        self.decompress = not self.isCompressed()
        if self.isB64():
            self.data = base64.b64decode(self.data)
            self.isPacked = True
        else:
            self.isPacked = False
        print(self.isPacked)

    def isB64(self):
        # Elegant AF: https://stackoverflow.com/a/45928164
        # Python wants a single "line" of base64...
        s = ''.join(self.data.splitlines())
        print(s)
        try:
            if base64.b64encode(base64.b64decode(self.data)) == s:
                print('is b64')
                return(True)
        except Exception:
            return(False)
        return(False)

    def isCompressed(self):
        pass

def parseArgs():
    args = argparse.ArgumentParser()
    args.add_argument('-z', '--compress',
                      dest = 'compress',
                      action = 'store_true',
                      help = ('If specified, compress the plugin when packing. (This will be detected and done automatically if needed for unpacking)'))
    args.add_argument('-f', '--file',
                      dest = 'file',
                      default = None,
                      help = 'If specified, use this file instead of STDIN for reading the plugin.')
    args.add_argument('-o', '--out',
                      dest = 'output',
                      default = None,
                      help = 'If specified, use this filepath instead of STDOUT for writing the result.')
    args.add_argument('operation',
                      choices = ['pack', 'unpack'],
                      help = 'Which operation to perform.')
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    if args['file']:
        args['file'] = os.path.abspath(os.path.expanduser(args['file']))
        with open(args['file'], 'rb') as f:
            plugindata = f.read()
    else:
        plugindata = sys.stdin.read()
    plugin = pluginParse(plugindata)

if __name__ == '__main__':
    main()