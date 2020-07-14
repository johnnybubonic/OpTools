#!/usr/bin/env python3

import argparse
try:
    import requests as handler
    has_req = True
except ImportError:
    from urllib.request import urlopen as handler
    has_req = False
try:
    import lxml
    parser = 'lxml'
except ImportError:
    parser = 'html.parser'
from bs4 import BeautifulSoup


def_elem = 'title'


class InfoScraper(object):
    def __init__(self, url, elem = def_elem, *args, **kwargs):
        self.url = url
        self.elem = elem
        self.raw = None
        self.str = None
        self.soup = None
        self._get_page()

    def _get_page(self):
        if has_req:
            self.raw = handler.get(self.url).content
        else:
            with handler(self.url) as fh:
                self.raw = fh.read()
        try:
            self.str = self.raw.decode('utf-8')
        except Exception:
            pass
        self.soup = BeautifulSoup(self.str, features = parser)
        return(None)

    def find(self):
        rtrn = [e for e in self.soup.find_all(self.elem)]
        return(rtrn)
        


def parseArgs():
    args = argparse.ArgumentParser(description = 'Get quick information from a URL at a glance')
    args.add_argument('-e', '--elem',
                      dest = 'elem',
                      default = def_elem,
                      help = ('The element(s) you want to scrape from the page. This is likely just going to be "{0}" (the default)').format(def_elem))
    args.add_argument('-s', '--strip',
                      dest = 'strip',
                      action = 'store_true',
                      help = ('If specified, strip whitespace at the beginning/end of each element text'))
    args.add_argument('-d', '--delineate',
                      dest = 'delin',
                      action = 'store_true',
                      help = ('If specified, delineate each element instance'))
    args.add_argument('-c', '--count',
                      dest = 'count',
                      action = 'store_true',
                      help = ('If specified, provide a count of how many times -e/--elem was found'))
    args.add_argument('url',
                      metavar = 'URL',
                      help = ('The URL to parse. It may need to be quoted or escaped depending on the URL and what shell you\'re using'))
    return(args)


def main():
    args = parseArgs().parse_args()
    i = InfoScraper(**vars(args))
    rslts = i.find()
    if args.count:
        print('Element {0} was found {1} time(s) at {2}. Results follow:'.format(args.elem, len(rslts), args.url))
    for i in rslts:
        t = i.text
        if args.strip:
            t = t.strip()
        if args.delin:
            print('== {0}: =='.format(args.elem))
        print(t)
        if args.delin:
            print('==\n')
    return(None)


if __name__ == '__main__':
    main()

