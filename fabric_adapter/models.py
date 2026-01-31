from dataclasses import dataclass
from typing import Any


@dataclass
class FabricRecord:
    patient_id: str
    priority: str
    threshold: int
    version: int
    encrypted_file_path: str
    encrypted_file_hash: str
    shares_wrapped: dict[str, str]
    timestamp: float
    audit_logs: list[dict[str, Any]]
