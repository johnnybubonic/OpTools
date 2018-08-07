#!/usr/bin/env python

import datetime
import subprocess
import time

def waiter(seconds = 1):
    prefix = ''
    idx = 0
    anims = ('|', '/', '-', '\\', 'O', '*', '\'', '^', '-', 'v', '_', '-')
    max = len(anims) - 1
    global is_done
    print('Beginning dhparam gen...')
    # This is just an example commant that takes a looong time.
    c = subprocess.Popen(['openssl', 'dhparam', '-out', '/tmp/dhpem', '4096'],
    #c = subprocess.Popen(['openssl', 'genrsa', '-out', '/tmp/dhpem', '4096'],
                         stdout = subprocess.PIPE,
                         stderr = subprocess.PIPE)
    print('dhparam gen started.')
    while c.poll() is None:
        #print('.', end = '', flush = True)
        try:
            char = anims[idx]
        except IndexError:
            exit()
        print('{0} => {1}'.format(prefix, char), end = '', flush = True)
        idx = (idx + 1 if idx < max else 0)
        prefix += '.'
        if seconds:
            time.sleep(seconds)
        #print('\b', end = '')
        print('\033[F')
    with open('/tmp/dhpem.out', 'w') as f:
        f.write(c.stdout.read().decode('utf-8'))
        f.write(c.stderr.read().decode('utf-8'))
    print('\nDone.')
    is_done = True

if __name__ == '__main__':
    waiter(1)
