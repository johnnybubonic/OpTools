#!/usr/bin/env python3

import argparse
import os
import re
import stat

class ConfStripper(object):
    def __init__(self, paths, comments = False, comment_syms = '#',
                 inline = True, whitespace = False, leading = True,
                 trailing = False, dry_run = False, symlinks = True):
        if __name__ == '__main__':
            # We're being run as a CLI utility, not an import.
            self.cli = True
        else:
            self.cli = False
        self.paths = self.paths_parser(paths)
        self.comments = comments
        self.comment_syms = comment_syms
        self.inline = inline
        self.whitespace = whitespace
        self.leading = leading
        self.trailing = trailing
        self.dry_run = dry_run
        self.symlinks = symlinks
        self.prep()

    def prep(self):
        self.regexes = []
        # In self.regexes, we group what we *keep* into group #1.
        if not self.comments:
            if len(self.comment_syms) == 1:
                if self.inline:
                    self.regexes.append(re.compile('^([^{0}]*){0}.*'.format(self.comment_syms[0])))
                else:
                    self.regexes.append(re.compile('^(\s*){0}.*'.format(self.comment_syms[0])))
            else:
                syms = '|'.join(self.comment_syms)
                if self.inline:
                    self.regexes.append(re.compile('^(.*)({0}).*'.format(syms)))
                else:
                    self.regexes.append(re.compile( '^(\s*)({0}).*'.format(syms)))
        return()

    def parse(self, path):
        if os.path.islink(path):
            if self.symlinks:
                # Check for a broken symlink
                try:
                    os.stat(path)
                except FileNotFoundError:
                    if self.cli:
                        print('{0}: Broken symlink'.format(path))
                    return(None)
            else:
                # We don't even WANT to follow symlinks.
                if self.cli:
                    print('{0}: Symlink'.format(path))
                return(None)
        if stat.S_ISSOCK(os.stat(path).st_mode):  # It's a socket
            if self.cli:
                print('{0}: Socket'.format(path))
            return(None)
        if stat.S_ISFIFO(os.stat(path).st_mode):  # It's a named pipe
            if self.cli:
                print('{0}: Named pipe'.format(path))
            return(None)
        try:
            with open(path, 'r') as f:
                conf = f.readlines()
        except UnicodeDecodeError:  # It's a binary file. Oops.
            if self.cli:
                print('{0}: Binary file? (is not UTF-8/ASCII)'.format(path))
            return(None)
        except PermissionError:
            if self.cli:
                print('{0}: Insufficient permission'.format(path))
            return(None)
        except Exception as e:
            if self.cli:
                print('{0}: {1}'.format(path, e))
            return(None)
        # Okay, so now we can actually parse.
        # Comments first.
        for idx, line in enumerate(conf):
            if line.strip() == '':
                continue
            for r in self.regexes:
                conf[idx] = r.sub('\g<1>', conf[idx])
            if conf[idx].strip() == '':  # The line was "deleted".
                conf[idx] = None
        conf = [i for i in conf if i is not None]
        # Then leading spaces...
        if not self.leading:
            for idx, line in enumerate(conf):
                conf[idx] = conf[idx].lstrip()
        # Then trailing spaces...
        if not self.trailing:
            for idx, line in enumerate(conf):
                conf[idx] = conf[idx].rstrip()
        # Lastly, if set, remove blank lines.
        if not self.whitespace:
            conf = [i for i in conf if i.strip() != '']
        return(conf)

    def recurse(self, path):
        files = []
        for r, d, f in os.walk(path):
            for i in f:
                files.append(os.path.join(r, i))
        return(files)

    def main(self):
        # Handle the files first.
        for p in self.paths['files']:
            try:
                new_content = '\n'.join(self.parse(p))
            except TypeError:  # Binary file, etc.
                continue
            self.writer(p, new_content)
        # Then the directories...
        for d in self.paths['dirs']:
            for f in self.recurse(d):
                try:
                    new_content = '\n'.join(self.parse(f))
                except TypeError:  # Binary file, etc.
                    continue
                self.writer(f, new_content)
        return()

    def writer(self, path, new_content):
        if self.dry_run:
            print('\n== {0} =='.format(path))
            print(new_content, end = '\n\n')
            return()
        try:
            with open(path, 'w') as f:
                f.write(new_content)
        except PermissionError:
            if self.cli:
                print('{0}: Cannot write (insufficient permission)'.format(path))
            return()
        return()

    def paths_parser(self, paths):
        realpaths = {'files': [],
                     'dirs': []}
        for p in paths:
            path = os.path.abspath(os.path.expanduser(p))
            if not os.path.exists(path):
                if self.cli:
                    print('{0} does not exist; skipping...'.format(path))
                continue
            if os.path.isfile(path):
                realpaths['files'].append(path)
            elif os.path.isdir(path):
                realpaths['dirs'].append(path)
        return(realpaths)

def parseArgs():
    args = argparse.ArgumentParser(description = ('Remove extraneous formatting/comments from files'))
    args.add_argument('-c', '--keep-comments',
                      dest = 'comments',
                      action = 'store_true',
                      help = ('If specified, retain all comments'))
    args.add_argument('-C', '--comment-symbol',
                      metavar = 'SYMBOL',
                      dest = 'comment_syms',
                      action = 'append',
                      default = [],
                      help = ('The character(s) to be treated as comments. '
                              'Can be specified multiple times (one symbol per flag, please, unless a specific '
                              'sequence denotes a comment). Default is just #'))
    args.add_argument('-i', '--no-inline',
                      dest = 'inline',
                      action = 'store_false',
                      help = ('If specified, do NOT parse the files as having inline comments (the default is to '
                              'look for inline comments)'))
    args.add_argument('-s', '--keep-whitespace',
                      dest = 'whitespace',
                      action = 'store_true',
                      help = ('If specified, retain whitespace'))
    args.add_argument('-t', '--keep-trailing',
                      dest = 'trailing',
                      action = 'store_true',
                      help = ('If specified, retain trailing whitespace on lines'))
    args.add_argument('-l', '--no-leading-whitespace',
                      dest = 'leading',
                      action = 'store_false',
                      help = ('If specified, REMOVE leading whitespace'))
    args.add_argument('-w', '--write',
                      dest = 'dry_run',
                      action = 'store_false',
                      help = ('If specified, overwrite the file(s) instead of just printing to stdout'))
    args.add_argument('-S', '--no-symlinks',
                      dest = 'symlinks',
                      action = 'store_false',
                      help = ('If specified, don\'t follow symlinks'))
    args.add_argument('paths',
                      metavar = 'PATH/TO/DIR/OR/FILE',
                      nargs = '+',
                      help = ('The path(s) to the file(s) to strip down. If a directory is given, files will '
                              'recursively be printed (unless -w/--write is specified). Can be specified multiple '
                              'times'))
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    if not args['comment_syms']:
        args['comment_syms'].append('#')
    c = ConfStripper(**args)
    c.main()

if __name__ == '__main__':
    main()
