#!/usr/bin/env python3

import argparse
import json
import os
import sys

def minify(json_in):
    j = json.loads(json_in)
    j = json.dumps(j, indent = None, separators = (',', ':'))
    return(j)

def parseArgs():
    args = argparse.ArgumentParser(description = ('Minify ("compress") JSON input'))
    args.add_argument('-o', '--output',
                      default = '-',
                      help = ('Write the minified JSON out to a file. The default is "-", which instead prints it to '
                              'STDOUT. If instead you would like to write out to STDERR, use "+" (otherwise provide a '
                              'path)'))
    args.add_argument('json_in',
                      default = '-',
                      nargs = '?',
                      help = ('The JSON input. If "-" (the default), read STDIN; otherwise provide a path to the '
                              'JSON file'))
    return(args)

def main():
    args = parseArgs().parse_args()
    if args.json_in.strip() == '-':
        stdin = sys.stdin.read()
        if not stdin:
            raise argparse.ArgumentError('You specified to read from STDIN, but STDIN is blank')
        else:
            args.json_in = stdin
    else:
        with open(os.path.abspath(os.path.expanduser(args.json_in)), 'r') as f:
            args.json_in = f.read()
    minified = minify(args.json_in)
    if args.output.strip() not in ('-', '+'):
        args.output = os.path.abspath(os.path.expanduser(args.output))
        if not args.output.endswith('.json'):
            args.output += '.json'
        with open(args.output, 'w') as f:
            f.write(minified + '\n')
    elif args.output.strip() == '+':
        sys.stderr.write(minified + '\n')
    else:
        sys.stdout.write(minified + '\n')
    return()

if __name__ == '__main__':
    main()