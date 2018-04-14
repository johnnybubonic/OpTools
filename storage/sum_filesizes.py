#!/usr/bin/env python3

# STDIN should be a list of "humanized" filesizes, e.g. 1.4G, 112K, etc.
# You should be able to get this with some careful grepping and awking.

import re
import sys

if sys.stdin.isatty():
    exit('You need to pipe in the file sizes you want summed.')

class BitFmtr(str):
    # https://bugs.python.org/msg123686
    def __format__(self, fmt):
        if fmt[0] == 'u':
            s = self.upper()
            fmt = fmt[1:]
        elif fmt[0] == 'l':
            s = self.lower()
            fmt = fmt[1:]
        else:
            s = str(self)
        return(s.__format__(fmt))

class deHumanizer(object):
    def __init__(self, lines_in):
        # lines_in should be a list of values to sum in "human" format.
        # Supports terabits/bytes down to single bit/bytes
        self.bytes = 0
        self.bits = 0
        self.sizes = [i.strip() for i in lines_in]
        _bytes = '^[0-9]+(\.[0-9]+)?\s*{0}B?$'
        _bits = '^[0-9]+(\.[0-9]+)?\s*({0:l}b?|{0:u}b)$'
        # Use a tuple. THe first item is the pattern to match, the second is
        # the multiplier to get it to bytes.
        # 1(TB) = 1099511627776 bytes/8796093022208 bits
        self.terabyte = (re.compile(_bytes.format('T')), 1099511627776)
        # 1 = 137438953472 bytes/1099511627776 bits
        self.terabit = (re.compile(_bits.format(BitFmtr('T'))), 137438953472)
        # 1 = 1073741824 bytes/8589934592 bits
        self.gigabyte = (re.compile(_bytes.format('G')), 1073741824)
        # 1 = 134217728 bytes/1073741824 bits
        self.gigabit = (re.compile(_bits.format(BitFmtr('G'))), 134217728)
        # 1 = 1048576 bytes/8388608 bits
        self.megabyte = (re.compile(_bytes.format('M')), 1048576)
        # 1 = 131072 bytes/1048576 bits
        self.megabit = (re.compile(_bits.format(BitFmtr('M'))), 131072)
        # 1 = 1024 bytes/8192 bits
        self.kilobyte = (re.compile(_bytes.format('K')), 1024)
        # 1 = 128 bytes/1024 bits
        self.kilobit = (re.compile(_bits.format(BitFmtr('K'))), 128)
        # 1 = 1 byte/8 bits
        # We don't use the pre-built pattern for these because you don't ever
        # see "## Bb" etc. Bytes are the default, IIRC, on Linux.
        self.byte = (re.compile('^[0-9]+(\.[0-9]+)?\s*B?$'), 1)
        # 1 = 0.125 bytes/1 bit
        self.bit = (re.compile('^[0-9]+(\.[0-9]+)?\s*b$'), 0.125)

    def convert(self):
        idx = 0
        for i in self.sizes[:]:
            try:
                _factor = float(re.sub('^([0-9\.]+)\s*.*$', '\g<1>', i))
            except ValueError:
                print('{0} does not seem to be a size; skipping'.format(i))
                self.sizes[idx] = 0  # Null it out since we couldn't parse it.
            # It's much more likely to be a smaller size than a larger one,
            # statistically-speaking, and more likely to be in bytes than bits.
            for r in (self.byte, self.kilobyte, self.megabyte, self.gigabyte,
                      self.terabyte, self.bit, self.kilobit, self.megabit,
                      self.gigabit, self.terabit):
                if r[0].search(i):
                    self.sizes[idx] = float(_factor * r[1])
                    idx += 1
                    break
#            # We didn't match, so remove it.
#            self.sizes[idx] = 0
#            idx += 1
        return()

    def get_sums(self):
        self.bytes = int(sum(self.sizes))
        self.bits = int(self.bytes * 8)
        self.kilobytes = int(self.bytes / self.kilobyte[1])
        self.kilobits = int(self.bytes / self.kilobit[1])
        self.megabytes = int(self.bytes / self.megabyte[1])
        self.megabits = int(self.bytes / self.megabit[1])
        self.gigabytes = int(self.bytes / self.gigabyte[1])
        self.gigabits = int(self.bytes / self.gigabit[1])
        self.terabytes = int(self.bytes / self.terabyte[1])
        self.terabits = int(self.bytes / self.terabit[1])
        return()

def main(data):
    dh = deHumanizer(data)
    dh.convert()
    dh.get_sums()
    print('TOTAL:')
    print('GB: {0}'.format(dh.gigabytes))
    print('Gb: {0}'.format(dh.gigabits))
    print('MB: {0}'.format(dh.megabytes))
    print('Mb: {0}'.format(dh.megabits))
    print('B:  {0}'.format(dh.bytes))
    print('b:  {0}'.format(dh.bits))
    return()

if __name__ == '__main__':
    main([i.strip() for i in sys.stdin.readlines() if i not in ('', '\n')])
