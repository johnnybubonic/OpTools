#!/usr/bin/env python3

import os
import argparse
import textwrap
import tarfile
import io
import re
import pydoc
from urllib.request import urlopen

# TODO: non-txt format support? (i.e. PDF, HTML, etc.)

def downloadRFC(destdir, rfcnum):
    rfcnum = (str(rfcnum)).lower()  # In case argparse interprets it as an int or it's entered in uppercase
    # For when we implement format support:
    # "plain" = raw text
    # "html" = html text
    # "pdf" = pdf text
    # "x-gzip" is for a gzipped presumably tarball, but we use the "all" keyword for this.
    filetypes = ['plain', 'html', 'pdf', 'x-gzip']
    filext = {}
    for t in filetypes:
        filext[t] = t
    filext['plain'] = 'txt'
    filext['x-gzip'] = 'txt'
    if rfcnum == 'all':
        rfcuri = 'https://www.rfc-editor.org/rfc/tar/RFC-all.tar.gz'
        rfctype = 'tar'
        filetype = 'x-gzip'
    else:
        rfcuri = 'https://tools.ietf.org/rfc/rfc{0}.txt'.format(rfcnum)
        rfctype = 'plain'  # We'll make use of this later.
        filetype = 'plain'
    rfcdir = '{0}/{1}'.format(destdir, filext[filetype])
    os.makedirs(rfcdir, exist_ok = True)
    # And some minor fixes. We don't need .txt extension for plaintype. Remove if someone complains.
    if filetype == 'plain':
        rfcpath = '{0}/{1}'.format(rfcdir, rfcnum)
    elif filetype == 'x-gzip':
        # We need to handle this a special way, since it's a gzipped tarball.
       rfcpath = rfcdir
    else:
        rfcpath = '{0}/{1}.{2}'.format(rfcdir, rfcnum, filext[filetype])
    with urlopen(rfcuri) as rfc:
        # Is this a single RFC, a release tarball, etc.
        # Commented out for now until we implement multi-format support, as we have the 'all' keyword to help us.
        #rfctype = rfc.response.info().get_content_subtype()
        # Handle the tarball here.
        if filetype == 'x-gzip':
            content = io.BytesIO(rfc.read())
            tarball = tarfile.open(fileobj = content)
            for i in tarball.getnames():
                filedest = '{0}/{1}'.format(rfcpath, re.sub('^rfc([0-9]+)\.txt$', '\g<1>', i))
                if re.match('^rfc[0-9]+\.txt$', i):
                    with tarball.extractfile(i) as e:
                        with open(filedest, 'wb') as f:
                            f.write(e.read())
        # We don't need to extract from the tarball, so we can just handle it as a plain read.
        else:
            content = rfc.read()
            with open(rfcpath, 'wb') as f:
                f.write(content)

def pageRFC(rfcnum):
    rfcnum = (str(rfcnum)).lower()  # In case argparse interprets it as an int or it's entered in uppercase
    with urlopen('https://tools.ietf.org/rfc/rfc{0}.txt'.format(rfcnum)) as rfc:
        pydoc.pager(rfc.read().decode('utf-8'))

def parseArgs():
    args = argparse.ArgumentParser(description = 'RFC Downloader/Viewer',
                                    epilog = 'TIP: this program has context-specific help. e.g. try "%(prog)s d -h"\nhttps://square-r00t.net/')
    subparsers = args.add_subparsers(help = 'Operation to perform', dest = 'operation')
    downloadargs = subparsers.add_parser('d', help = 'Download an RFC/RFCs.')
    pagerargs = subparsers.add_parser('p', help = 'Print the RFC to the terminal.')  # TODO: add -b/--browser? redirect to lynx for html paging?
    downloadargs.add_argument('-d',
                        '--destination',
                        dest = 'destdir',
                        metavar = 'DESTINATION',
                        default = '/usr/local/share/doc/rfc',
                        help = 'The destination directory to save the RFC to. Will be created if it doesn\'t exist (assuming we have permissions). The default is /usr/local/share/doc/rfc/.')
    downloadargs.add_argument(dest = 'rfcnum',
                        metavar = 'RFC',
                        default = 'all',
                        help = 'The RFC number. If the special value "all" is used, then ALL of the published RFCs will be fetched.')
    pagerargs.add_argument(dest = 'rfcnum',
                        metavar = 'RFC',
                        help = 'The RFC number.')
    return(args)

def main():
    argsin = parseArgs()
    args = argsin.parse_args()
    if args.operation == 'd':
        downloadRFC(args.destdir, args.rfcnum)
    elif args.operation == 'p':
        pageRFC(args.rfcnum)
    else:
        argsin.print_help()   

if __name__ == '__main__':
    main()
