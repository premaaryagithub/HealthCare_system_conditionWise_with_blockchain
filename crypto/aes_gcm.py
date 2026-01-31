import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass(frozen=True)
class AesGcmEncrypted:
    nonce: bytes
    ciphertext: bytes


def encrypt(key: bytes, plaintext: bytes, aad: bytes | None = None) -> AesGcmEncrypted:
    if len(key) != 32:
        raise ValueError("AES-256 key must be 32 bytes")
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, plaintext, aad)
    return AesGcmEncrypted(nonce=nonce, ciphertext=ct)


def decrypt(key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes | None = None) -> bytes:
    if len(key) != 32:
        raise ValueError("AES-256 key must be 32 bytes")
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, aad)
