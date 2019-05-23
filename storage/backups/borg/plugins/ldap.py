import os
# TODO: virtual env?
import ldap
import ldif


# Designed for use with OpenLDAP in an OLC configuration.


class Backup(object):
    def __init__(self,
                 server = 'ldap://sub.domain.tld',
                 port = 389,
                 basedn = 'dc=domain,dc=tld',
                 sasl = False,
                 starttls = True,
                 binddn = 'cn=Manager,dc=domain,dc=tld',
                 password_file = '~/.ldap.pass',
                 password = None,
                 outdir = '~/.cache/backup/ldap',
                 splitldifs = True):
        self.server = server
        self.port = port
        self.basedn = basedn
        self.sasl = sasl
        self.binddn = binddn
        self.outdir = os.path.abspath(os.path.expanduser(outdir))
        os.makedirs(self.outdir, exist_ok = True)
        self.splitldifs = splitldifs
        self.starttls = starttls
        if password_file and not password:
            with open(os.path.abspath(os.path.expanduser(password_file)), 'r') as f:
                self.password = f.read().strip()
        else:
            self.password = password
        # Human readability, yay.
        # A note, SSLv3 is 0x300. But StartTLS can only be done with TLS, not SSL, I *think*?
        # PRESUMABLY, now that it's finalized, TLS 1.3 will be 0x304.
        # See https://tools.ietf.org/html/rfc5246#appendix-E
        self._tlsmap = {'1.0': int(0x301),  # 769
                        '1.1': int(0x302),  # 770
                        '1.2': int(0x303)}  # 771
        self._minimum_tls_ver = '1.2'
        if self.sasl:
            self.server = 'ldapi:///'
        self.cxn = None
        self.connect()
        self.dump()
        self.close()

    def connect(self):
        self.cxn = ldap.initialize(self.server)
        self.cxn.set_option(ldap.OPT_REFERRALS, 0)
        self.cxn.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
        if not self.sasl:
            if self.starttls:
                self.cxn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
                self.cxn.set_option(ldap.OPT_X_TLS, ldap.OPT_X_TLS_DEMAND)
                self.cxn.set_option(ldap.OPT_X_TLS_DEMAND, True)
                self.cxn.set_option(ldap.OPT_X_TLS_PROTOCOL_MIN, self._tlsmap[self._minimum_tls_ver])
        if self.sasl:
            self.cxn.sasl_external_bind_s()
        else:
            if self.starttls:
                self.cxn.start_tls_s()
            self.cxn.bind_s(self.binddn, self.password)
        return()

    def dump(self):
        dumps = {'schema': 'cn=config',
                 'data': self.basedn}
        with open(os.path.join(self.outdir, ('ldap-config.ldif' if self.splitldifs else 'ldap.ldif')), 'w') as f:
            l = ldif.LDIFWriter(f)
            rslts = self.cxn.search_s(dumps['schema'],
                                      ldap.SCOPE_SUBTREE,
                                      filterstr = '(objectClass=*)',
                                      attrlist = ['*', '+'])
            for r in rslts:
                l.unparse(r[0], r[1])
        if self.splitldifs:
            f = open(os.path.join(self.outdir, 'ldap-data.ldif'), 'w')
        else:
            f = open(os.path.join(self.outdir, 'ldap.ldif'), 'a')
        rslts = self.cxn.search_s(dumps['data'],
                                  ldap.SCOPE_SUBTREE,
                                  filterstr = '(objectClass=*)',
                                  attrlist = ['*', '+'])
        l = ldif.LDIFWriter(f)
        for r in rslts:
            l.unparse(r[0], r[1])
        f.close()

    def close(self):
        if self.cxn:
            self.cxn.unbind_s()
        return()
