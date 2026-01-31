from __future__ import annotations

import os
import requests

from fabric_adapter.models import FabricRecord


class FabricRestAdapter:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        ssl_verify = (os.getenv("FABRIC_SSL_VERIFY") or "true").strip().lower()
        self.verify = ssl_verify not in {"0", "false", "no", "off"}

    def createRecord(self, record: FabricRecord) -> None:
        r = self.session.post(f"{self.base_url}/records", json=_to_dict(record), timeout=30, verify=self.verify)
        _raise_for_status(r)

    def updateRecord(self, record: FabricRecord) -> None:
        r = self.session.put(
            f"{self.base_url}/records/{record.patient_id}",
            json=_to_dict(record),
            timeout=30,
            verify=self.verify,
        )
        _raise_for_status(r)

    def getLatestRecord(self, patient_id: str) -> FabricRecord:
        r = self.session.get(f"{self.base_url}/records/{patient_id}/latest", timeout=30, verify=self.verify)
        _raise_for_status(r)
        return _from_dict(r.json())

    def getHistory(self, patient_id: str) -> list[FabricRecord]:
        r = self.session.get(f"{self.base_url}/records/{patient_id}/history", timeout=30, verify=self.verify)
        _raise_for_status(r)
        data = r.json()
        return [_from_dict(x) for x in data.get("history", [])]

    def appendAuditLog(self, patient_id: str, audit_entry: dict) -> None:
        r = self.session.post(
            f"{self.base_url}/records/{patient_id}/audit",
            json=audit_entry,
            timeout=30,
            verify=self.verify,
        )
        _raise_for_status(r)


def _raise_for_status(r: requests.Response) -> None:
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        raise ValueError(r.text) from e


def _to_dict(record: FabricRecord) -> dict:
    return {
        "patient_id": record.patient_id,
        "priority": record.priority,
        "threshold": record.threshold,
        "version": record.version,
        "encrypted_file_path": record.encrypted_file_path,
        "encrypted_file_hash": record.encrypted_file_hash,
        "shares_wrapped": record.shares_wrapped,
        "timestamp": record.timestamp,
        "audit_logs": record.audit_logs,
    }


def _from_dict(d: dict) -> FabricRecord:
    return FabricRecord(
        patient_id=d["patient_id"],
        priority=d["priority"],
        threshold=int(d["threshold"]),
        version=int(d["version"]),
        encrypted_file_path=d["encrypted_file_path"],
        encrypted_file_hash=d["encrypted_file_hash"],
        shares_wrapped=dict(d["shares_wrapped"]),
        timestamp=float(d["timestamp"]),
        audit_logs=list(d.get("audit_logs", [])),
    )
