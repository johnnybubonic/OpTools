#!/usr/bin/env python3

import copy
import pprint
import usrmgmt2

# NOTE: THIS IS ONLY FOR TESTING/DEVELOPMENT PURPOSES.
# IT WILL BE REMOVED ONCE THE ACTUAL STUFF IS FINISHED.

args = vars(usrmgmt2.parseArgs().parse_args())
args['operation'] = 'ls'
args['verbose'] = True
args['cfgfile'] = '/home/bts/.config/optools/mumbleadmin.ini'
#if not args['operation']:
    #raise RuntimeError('You must specify an operation to perform. Try running with -h/--help.')
#    exit('You must specify an operation to perform. Try running with -h/--help.')

mgmt = usrmgmt2.IceMgr(args)

def dictify(obj):
    # thanks, https://github.com/alfg/murmur-rest/blob/master/app/utils.py
    _rv = {'_type': str(type(obj))}
    if type(obj) in (bool, int, float, str, bytes):
        return(obj)
    if type(obj) in (list, tuple):
        return([dictify(i) for i in obj])
    if type(obj) == dict:
        return(dict((str(k), dictify(v)) for k, v in obj.items()))
    return(dictify(obj.__dict__))


# Here we actually print users
#print(inspect.getmembers(Murmur.UserInfo))
#for s in mgmt.conn['read'].getAllServers():  # iterate through all servers
    #userattrs = [Murmur.UserInfo.Username, Murmur.UserInfo.UserEmail,
    #             Murmur.UserInfo.UserHash, Murmur.UserInfo.UserLastActive,
    #             Murmur.UserInfo.UserComment]
    #print(type(s))
    #pprint.pprint(s.getRegisteredUsers(''))  # either print a UID:username map...
#    for uid, uname in s.getRegisteredUsers('').items():  # or let's try to get full info on them
        #print('user: {0}\nusername: {1}\n'.format(uid, uname))
#        _u = dictify(s.getRegistration(uid))
#        if uid == 3:
#            print(_u)

print(mgmt.conn['read'])
_server = mgmt.conn['read'].getServer(1)

print(_server.getACL(0))

#acl = _server.getACL(0)
#print(acl[0])



#pprint.pprint(dictify(acl), indent = 4)

mgmt.close()
