#!/usr/bin/env python3

# Thanks to https://gist.github.com/stantonk/7268449
# See also:
# http://stackoverflow.com/questions/5480131/will-python-systemrandom-os-urandom-always-have-enough-entropy-for-good-crypto
import argparse
import random
import re
import string

class genPass(object):
    def __init__(self, case = None, charset = 'complex', passlen = 32, quotes = True, backslashes = True,
                 human = False):
        # complex is symbols and mixed-case alphanumeric
        # simple is mixed-case alphanumeric
        _alphanum = string.ascii_letters + string.digits
        chars = {'complex': _alphanum + string.punctuation,
                 'simple': _alphanum}
        self.chars = chars[charset]
        if not quotes:
            self.chars = re.sub('["\']', '', self.chars)
        if not backslashes:
            self.chars = re.sub('\\\\', '', self.chars)
        if human:
            _dupechars = ['`', "'", '|', 'l', 'I', 'i', 'l', '1', 'o', '0', 'O']
            self.chars = ''.join(sorted(list(set(self.chars) - set(_dupechars))))
        if case == 'upper':
            self.chars = self.chars.upper()
        elif case == 'lower':
            self.chars = self.chars.lower()
        self.chars = ''.join(sorted(list(set(self.chars))))
        self.passlen = passlen

    def generate(self):
        self.pw = ''
        for _ in range(self.passlen):
            self.pw += random.SystemRandom().choice(self.chars)

def parseArgs():
    args = argparse.ArgumentParser(description = 'A password generator.')
    args.add_argument('-t', '--type',
                      dest = 'passtype',
                      choices = ['simple', 'complex'],  # chars in genPass
                      default = 'complex',
                      help = ('Whether to generate "simple" (no symbols, '
                              'safer for e.g. databases) password(s) or more complex ones. The default is "complex"'))
    args.add_argument('-l', '--length',
                      dest = 'passlen',
                      metavar = 'LENGTH',
                      type = int,
                      default = 32,
                      help = ('The length of the password(s) to generate. The default is 32'))
    args.add_argument('-c', '--count',
                      dest = 'passcount',
                      metavar = 'COUNT',
                      type = int,
                      default = 1,
                      help = ('The number of passwords to generate. The default is 1'))
    args.add_argument('-q', '--no-quotes',
                      dest = 'quotes',
                      action = 'store_false',
                      help = ('If specified, strip out quotation marks (both " and \') from the passwords. '
                              'Only relevant if -t/--type is complex, as simple types don\'t contain these'))
    args.add_argument('-b', '--no-backslashes',
                      dest = 'backslashes',
                      action = 'store_false',
                      help = ('If specified, strip out backslashes. Only relevant if -t/--type is complex, as '
                              'simple types don\'t contain these'))
    args.add_argument('-H', '--human',
                      dest = 'human',
                      action = 'store_true',
                      help = ('If specified, make the passwords easier to read by human eyes (i.e. no 1 and l, '
                              'o or O or 0, etc.)'))
    caseargs = args.add_mutually_exclusive_group()
    caseargs.add_argument('-L', '--lower',
                          dest = 'case',
                          action = 'store_const',
                          const = 'lower',
                          help = 'If specified, make password all lowercase')
    caseargs.add_argument('-U', '--upper',
                          dest = 'case',
                          action = 'store_const',
                          const = 'upper',
                          help = 'If specified, make password all UPPERCASE')
    return(args)

def main():
    args = vars(parseArgs().parse_args())
    for _ in range(0, args['passcount']):
        p = genPass(charset = args['passtype'], passlen = args['passlen'],
                    quotes = args['quotes'], backslashes = args['backslashes'],
                    human = args['human'], case = args['case'])
        p.generate()
        print(p.pw)

if __name__ == '__main__':
    main()