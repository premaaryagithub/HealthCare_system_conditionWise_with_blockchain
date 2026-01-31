import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class PeerNMKStore:
    def __init__(self, base_dir: str, peer_ids: list[str]):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
        self.peer_ids = peer_ids
        for pid in peer_ids:
            self._ensure(pid)

    def _ensure(self, peer_id: str) -> None:
        path = os.path.join(self.base_dir, f"{peer_id}.key")
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(os.urandom(32))

    def _load(self, peer_id: str) -> bytes:
        path = os.path.join(self.base_dir, f"{peer_id}.key")
        with open(path, "rb") as f:
            key = f.read()
        if len(key) != 32:
            raise ValueError("invalid NMK")
        return key

    def wrap_share(self, peer_id: str, share: bytes, aad: bytes) -> str:
        key = self._load(peer_id)
        nonce = os.urandom(12)
        ct = AESGCM(key).encrypt(nonce, share, aad)
        return base64.b64encode(nonce + ct).decode("utf-8")

    def unwrap_share(self, peer_id: str, wrapped_b64: str, aad: bytes) -> bytes:
        key = self._load(peer_id)
        blob = base64.b64decode(wrapped_b64)
        nonce = blob[:12]
        ct = blob[12:]
        return AESGCM(key).decrypt(nonce, ct, aad)
