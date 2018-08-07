#!/usr/bin/env python3

# requires python lxml module as well
import os
import socket
import time
from urllib.request import urlopen
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# The page that contains the list of (authoritative ISO) mirrors
URL = 'http://isoredirect.centos.org/centos/7/isos/x86_64/'
# The formatting on the page is pretty simple - no divs, etc. - so we need to
# blacklist some links we pull in.
blacklisted_link_URLs = ('http://bittorrent.com/',
                         'http://wiki.centos.org/AdditionalResources/Repositories')

mirrors = {}

dflt_ports = {'https': 443,  # unlikely. "HTTPS is currently not used for mirrors." per https://wiki.centos.org/HowTos/CreatePublicMirrors
              'http': 80,  # most likely.
              'ftp': 21,
              'rsync': 873}

def getMirrors():
    mirrors = []
    with urlopen(URL) as u:
        pg_src = u.read().decode('utf-8')
    soup = BeautifulSoup(pg_src, 'lxml')
    for tag in soup.find_all('br')[4].next_siblings:
        if tag.name == 'a' and tag['href'] not in blacklisted_link_URLs:
            mirrors.append(tag['href'].strip())
    return(mirrors)

def getHosts(mirror):
    port = None
    fqdn = None
    login = ''
    # "mirror" should be a base URI of the CentOS mirror path.
    # mirrors.centos.org is pointless to use for this!
    #url = os.path.join(mirror, 'sha256sum.txt.asc')
    uri = urlparse(mirror)
    spl_dom = uri.netloc.split(':')
    if len(spl_dom) >= 2:  # more complex URI
        if len(spl_dom) == 2:  # probably domain:port?
            try:
                port = int(spl_dom[-1:])
            except ValueError:  # ooookay, so it's not domain:port, it's a user:pass@
                if '@' in uri.netloc:
                    auth = uri.netloc.split('@')
                    fqdn = auth[1]
                    login = auth[0] + '@'
        elif len(spl_dom) > 2:  # even more complex URI, which ironically makes parsing easier
            auth = uri.netloc.split('@')
            fqdn = spl_dom[1].split('@')[1]
            port = int(spl_dom[-1:])
            login = auth[0] + '@'
    # matches missing values and simple URI. like, 99%+ of mirror URIs being passed.
    if not fqdn:
        fqdn = uri.netloc
    if not port:
        port = dflt_ports[uri.scheme]
    mirrors[fqdn] = {'proto': uri.scheme,
                     'port': port,
                     'path': uri.path,
                     'auth': login}
    return()

def getSpeeds():
    for fqdn in mirrors.keys():
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((fqdn, mirrors[fqdn]['port']))
        mirrors[fqdn]['time'] = time.time() - start
        sock.close()
    return()

def main():
    for m in getMirrors():
        getHosts(m)
    getSpeeds()
    ranking = sorted(mirrors.keys(), key = lambda k: (mirrors[k]['time']))
    for i in ranking:
        str_port = ':' + str(mirrors[i]['port'])
        if mirrors[i]['port'] in dflt_ports.values():
            str_port = ''
        print('{proto}://{auth}{0}{p}{path}'.format(i,
                                                    **mirrors[i],
                                                    p = str_port))

if __name__ == '__main__':
    main()
