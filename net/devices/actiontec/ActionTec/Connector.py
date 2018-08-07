#!/usr/bin/env python3.6

# stdlib
import re
import socket

def CheckConnection(host, port):
    # We favor socket over telnetlib's check because it has a little better
    # handling of exceptions.
    try:
        port = int(port)  # just in case we were passed a str()
    except ValueError:
        raise ValueError('"{0}" is not a port number'.format(port))
        # In case they're catching the exception...
        return(False)
    s = socket.socket()
    try:
        s.connect((host, port))
    except Exception as e:
        raise RuntimeError(('We were unable to successfully connect to ' +
                            '"{0}:{1}": {2}').format(host, port, e))
        return(False)
    finally:
        s.close()
    return(True)

def Login(host, port, ssl, user, password):
    user_prompt = [re.compile('^\s*user(name)?\s*:?\s*'.encode('utf-8'),
                              re.IGNORECASE)]
    passwd_prompt = [re.compile('^\s*passw(or)d?\s*:?\s*'.encode('utf-8'),
                                re.IGNORECASE)]
    # Are there any other valid chars? Will need to experiment.
    # How is this even set? The default is "Wireless Broadband Router".
    # I think it can't be changed, at least via the Web GUI.
    cmd_prompt = [re.compile('[-_a-z0-9\s]*>'.encode('utf-8'),
                             re.IGNORECASE)]
    ctx = None
    ctxargs = {'host': host, 'port': port}
    try:
        if ssl:
            try:
                from ssltelnet import SslTelnet as telnet
                ctxargs['force_ssl'] = True
            except ImportError:
                raise ImportError(('You have enabled SSL but do not have ' +
                                   'the ssltelnet module installed. See ' +
                                   'the README file, footnote [1].'))
        else:
            from telnetlib import Telnet as telnet
        ctx = telnet(**ctxargs)
        ctx.expect(user_prompt, timeout = 8)
        ctx.write((user + '\n').encode('utf-8'))
        ctx.expect(passwd_prompt, timeout = 8)
        ctx.write((password + '\n').encode('utf-8'))
        ctx.expect(cmd_prompt, timeout = 15)
    except EOFError:
        if ctx:
            ctx.close()
            ctx = None
    except Exception as e:
        raise RuntimeError(('We encountered an error when trying to connect:' +
                            ' {0}').format(e))
        if ctx:
            ctx.close()
            ctx = None
    return(ctx)