#!/usr/bin/env python3

# https://tools.ietf.org/html/rfc2317
# https://tools.ietf.org/html/rfc4183
desc = 'Gets the RFC 2317/4183 PTR of given IP addresses or A/AAAA records.' 

# stdlib
import argparse
import copy
import ipaddress
import os
# pypi/pip
#try:
#    import ipwhois
#except ImportError:
#    exit('You need to install the ipwhois module.')
try:
    import dns.resolver
    import dns.reversename
except ImportError:
    exit('You need to install the dnspython module.')
try:
    import fqdn
except ImportError:
    exit('You need to install the fqdn module.')

def resolveRecord(addr):
    r = dns.resolver.Resolver()
    ipaddrs = {'A': [],
               'AAAA': []}
    for rtype in ipaddrs.keys():
        for record in r.query(addr, 'A'):
            ipaddrs[rtype].append(record)
    ipaddrs['ipv4'] = sorted(list(set(copy.deepcopy(ipaddrs['A']))))
    ipaddrs['ipv6'] = sorted(list(set(copy.deepcopy(ipaddrs['AAAA']))))
    del(ipaddrs['A'], ipaddrs['AAAA'])
    if ipaddrs['ipv4'] == ipaddrs['ipv6']:
        del(ipaddrs['ipv6'])
    return(ipaddrs)

def genPTR(ipaddr, iptype):
    _suffix = ''
    # TODO: get the current PTR.
    # TODO: do this more manually. We should use ipaddress and ipwhois to get
    #       the proper return for e.g. network gateways.
    return(dns.reversename.from_address(ipaddr))

def chkInput(src):
    # Determine the input, if we can.
    src_out = (None, None)
    try:
        ipaddress.IPv4Address(src)
        return(('ipv4', src))
    except ipaddress.AddressValueError:
        pass
    try:
        ipaddress.IPv6Address(src)
        return(('ipv6', src))
    except ipaddress.AddressValueError:
        pass
    _p = os.path.abspath(os.path.expanduser(src))
    if os.path.isfile(_p):
        return(('file', _p))
    # Last shot - is it a DNS record?
    # Not quite perfect, as it's strictly RFC and there are plenty of
    # subdomains out there that break RFC.
    f = fqdn.FQDN(src)
    if f.is_valid:
        return(('dns', src))
    return(src_out)

def parseArgs():
    def chkArg(src):
        src_out = chkInput(src)
        if src_out == (None, None):
            raise argparse.ArgumentTypeError(('"{0}" does not seem to be a ' +
                                              'path to a file, an A/AAAA ' +
                                              'record, or IPv4/IPv6 ' +
                                              'address.').format(src))
        return(src_out)
    args = argparse.ArgumentParser(description = desc)
    args.add_argument('data_in',
                      type = chkArg,
                      metavar = 'ADDRESS_OR_FILE',
                      help = ('The path to a file containing domains and IP ' +
                              'addresses OR a single IPv4/IPv6 address or ' +
                              'A/AAAA record. If an A/AAAA record, your ' +
                              'machine must be able to resolve it (and it ' +
                              'must exist)'))
    return(args)

def main():
    # TODO: clean this up, migrate the duplicated code into a func
    args = vars(parseArgs().parse_args())['data_in']
    if args[0] == 'dns':
        r = resolveRecord(args[1])
        for k in r.keys():
            for ip in r[k]:
                print('IP: {0}'.format(ip))
                print('PTR: {0}'.format(genPTR(str(ip), k)))
    elif args[0] in ('ipv4', 'ipv6'):
        print('PTR: {0}'.format(genPTR(args[1], args[0])))
    elif args[0] == 'file':
        with open(args[1], 'r') as f:
            recordlst = [i.strip() for i in f.readlines()]
        for i in recordlst:
            ltype, data = chkInput(i)
            print('== {0} =='.format(i))
            if ltype == 'dns':
                r = resolveRecord(data)
                for k in r.keys():
                    for ip in r[k]:
                        print('IP: {0}'.format(ip))
                        print('PTR: {0}'.format(genPTR(str(ip), k)))
            elif ltype in ('ipv4', 'ipv6'):
                print('PTR: {0}'.format(genPTR(data, ltype)))
            print()

if __name__ == '__main__':
    main()
