import hashlib
import os


class LocalObjectStore:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def put(self, patient_id: str, version: int, blob: bytes, condition: str | None = None) -> tuple[str, str]:
        condition_norm = (condition or "general").strip() or "general"
        d = os.path.join(self.base_dir, condition_norm, patient_id)
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"v{version}.bin")
        with open(path, "wb") as f:
            f.write(blob)
        h = hashlib.sha256(blob).hexdigest()
        return path, h

    def get(self, path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    def hash(self, blob: bytes) -> str:
        return hashlib.sha256(blob).hexdigest()
