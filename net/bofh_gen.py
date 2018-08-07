#!/usr/bin/env python

import telnetlib
import time

counter = 8

def get_excuse():
    # http://www.blinkenlights.nl/services.html
    # port 23 (default) is Star Wars.
    # port 666 is BOfH excuses
    with telnetlib.Telnet('towel.blinkenlights.nl', port = 666) as t:
        excuse = [x.decode('utf-8').strip() \
                                    for x in t.read_all().split(b'===\r\n')]
    return(excuse[2])

def main():
    for i in range(counter):
        e = get_excuse()
        print(e)
        time.sleep(1)

if __name__ == '__main__':
    main()
