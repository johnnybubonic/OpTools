#!/usr/bin/env python3
# https://gist.github.com/akshaybabloo/2a1df455e7643926739e934e910cbf2e

import ipaddress
import dns  # apacman -S python-dnspython
import ipwhois  # apacman -S python-ipwhois
import whois  # apacman -S python-ipwhois

class netTarget(object):
    def __init__(self, target):
        self.target = target


##!/usr/bin/env python3
#
#import pprint
#import dns
#import whois
#import ipwhois
#
#d = 'sysadministrivia.com'  # A/AAAA
#d = 'autoconfig.sysadministrivia.com'  # CNAME
#
#records = {'whois': None,
#           'ptr': None,
#           'allocation': None}
#
#def getWhois(domain):
#    _w = whois.whois(d)
#    records['whois'] = dict(_w)
#    return()
#
#def getIps(domain):
#    addrs = []
#    for t in ('A', 'AAAA'):
#        answers = dns.resolver.query(domain, t)
#        for a in answers:
#            try:
#                addrs.append(a.address)
#            except:
#                pass
#    return(addrs)
#
#def getPtr(addrs):
#    for a in addrs:
#        pass
#
#print(getIps(d))
##pprint.pprint()
