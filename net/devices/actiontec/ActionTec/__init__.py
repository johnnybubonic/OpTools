#!/usr/bin/env python3.6

import .Cmd as Cmd
import .Connector as Connector

class Router(object):
    def __init__(self, host, port, user, password, ssl = False):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.ssl = ssl
        self.ctx = None
        # Convenient shorthand. See "help.all.txt".
        self.cmds = {'reboot': 'system reboot',
                     'wipe': 'conf factory restore',
                     # this will... require an interactive session
                     'shell': 'system shell'}
        
    def connect(self):
        # We don't need to define an except, really.
        # The function handles that for us.
        Connector.CheckConnection(self.host, self.port)
        self.ctx = Connector.Login(self.host, self.port, self.ssl, self.user,
                                   self.password)
        return()
    
    def execute(self):
        pass
    
    def close(self):
        if self.ctx:
            self.ctx.close()