#!/usr/bin/env python3

# Parse existing keys

class constructor(object):
    # These are various struct formats for the "new"-style OpenSSH private keys.
    # REF1: https://cvsweb.openbsd.org/cgi-bin/cvsweb/src/usr.bin/ssh/PROTOCOL.key?annotate=1.1
    # REF2: https://github.com/openssh/openssh-portable/blob/94bc1e7ffba3cbdea8c7dcdab8376bf29283128f/sshkey.c
    def __init__(self, ssh_keyblob):
        # "keyblob" is the raw binary of an extracted (i.e. "---...---"-removed) and un-base64'd private key.
        self.keyblob = ssh_keyblob
        # 'encrypted' if it's encrypted, 'none' if plaintext. This is determined via processing.
        self.enctype = 'none'
        # This is the header. It is used by both encrypted and unencrypted keys.
        self.header = ''.join((
                            '14cx', # "openssh-key-v1" and null byte (6f70656e7373682d6b65792d7631 00) ("magic bytes")
                            'i'     # separator, always 00000004
                            ))
        # Only two cipher types that I know of that are used.
        self.ciphertype = {
                            'none': '4c',           # 6e6f6e65
                            'aes256-cbc': '10c'}    # 6165733235362d636263 ("aes256-cbc")
        # This separator is present in both.
        self.sep1 = 'i'
        # The name of the key encryption, if encrypted. These are the only two I know of that are used.
        self.kdfname = {
                            'none': '4c',       # 6e6f6e65 ("none")
                            'bcrypt': '6c'}     # 626372797074 ("bcrypt")
        ########################################### ENCRYPTED KEYS ONLY ################################################
        # KDF options
        self.kdfopts = {
                            'none': '0i',       # zero-length
                            'encrypted': '24i'} # 24-length int
        # The length of the salt. Default is 16 (REF2:67)
        self.saltlen = {
                            'none': '0i',       # TODO: do unencrypted still have salts?
                            'encrypted': '4i'}  # 16 bytes length?
        # The key needs to be parsed incrementally to have these lengths adjusted.
        self.salt = {
                            'none': '0c',
                            'encrypted': '4c'}  # This value may change based on self.saltlen['encrypted']'s value.
        # The number of rounds for the key; default is 16 (REF2:69).
        self.rounds = {
                            'none': '0i',       # TODO: do unencrypted still have rounds?
                            'encrypted': '16i'}
        ################################################################################################################
        # Number of public keys.
        self.numpub = 'i'
        # That's all we can populate now. The rest is handled below via functions.
        self._chkencrypt()

    def _chkencrypt(self):
        pass


class legacy_constructor(object):
    # These are various struct formats for the "old"-style OpenSSH private keys.
    def __init__(self, keyblob):
        self.keyblob = keyblob
