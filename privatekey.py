import os
import binascii
import base58
import hashlib

class PrivateKey:
    def __init__(self, private_key=None):
        # Constructor for the PrivateKey class
        # Initializes the instance variables and generates a random 32 byte private key
        if private_key is None:
            self.private_key = os.urandom(32)
        else:
            self.private_key = private_key
        self.passphrase = None
        self.wif = None

    def from_passphrase(self, passphrase):
        # Function to generate a private key from a given passphrase
        # Uses a cryptographically secure random number generator to generate a 32 byte private key from the passphrase
        # and then hashes it with SHA256
        private_key = hashlib.sha256(passphrase.encode('utf-8')).digest()
        self.private_key = private_key
        self.passphrase = passphrase
        self.wif = None
        return private_key

    def privatekey_to_wif(self, private_key=None, compressed=False):
        # Function to convert a given private key to a Wallet Import Format (WIF)
        # If no private key is provided, uses the instance variable
        # If compressed=True, the WIF is generated for a compressed public key
        if private_key is None:
            private_key = self.private_key
        else:
            private_key = private_key
        if compressed:
            extented_key = b"\x80" + private_key + b"\x01"
        else:
            extented_key = b"\x80" + private_key
        first_sha256 = hashlib.sha256(extented_key).digest()
        second_sha256 = hashlib.sha256(first_sha256).digest()
        final_key = extented_key + second_sha256[:4]
        wif = base58.b58encode(final_key).decode("utf-8")
        self.wif = wif
        return wif
