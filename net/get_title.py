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
        if len(rtrn) == 1:
            rtrn = rtrn[0]
        elif len(rtrn) == 0:
            rtrn = None
        return(rtrn)
        


def parseArgs():
    args = argparse.ArgumentParser(description = 'Get quick information from a URL at a glance')
    args.add_argument('-e', '--elem',
                      default = def_elem,
                      help = ('The element(s) you want to scrape from the page. This is likely just going to be "{0}" (the default)').format(def_elem))
    args.add_argument('url',
                      metavar = 'URL',
                      help = ('The URL to parse. It may need to be quoted or escaped depending on the URL and what shell you\'re using'))
    return(args)


def main():
    args = parseArgs().parse_args()
    i = InfoScraper(**vars(args))
    rslts = i.find()
    if isinstance(rslts, list):
        for i in rslts:
            print('== {0}: =='.format(args.elem))
            print(i.text.strip())
            print('==\n')
    else:
        print('== {0}: =='.format(args.elem))
        print(rslts.text.strip())
        print('==')
    return(None)


if __name__ == '__main__':
    main()

