import json
import os
import time
from typing import Any

from fabric_adapter.models import FabricRecord


class MockFabricAdapter:
    def __init__(self, ledger_path: str):
        self.ledger_path = ledger_path
        os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
        if not os.path.exists(ledger_path):
            with open(ledger_path, "w", encoding="utf-8") as f:
                json.dump({"patients": {}}, f)

    def _load(self) -> dict[str, Any]:
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: dict[str, Any]) -> None:
        tmp = self.ledger_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.ledger_path)

    def createRecord(self, record: FabricRecord) -> None:
        data = self._load()
        patients = data.setdefault("patients", {})
        if record.patient_id in patients and len(patients[record.patient_id]) > 0:
            raise ValueError("patient already exists")
        patients[record.patient_id] = [self._to_dict(record)]
        self._save(data)

    def updateRecord(self, record: FabricRecord) -> None:
        data = self._load()
        patients = data.setdefault("patients", {})
        history = patients.setdefault(record.patient_id, [])
        if history and int(history[-1].get("version", -1)) == int(record.version):
            history[-1] = self._to_dict(record)
        else:
            history.append(self._to_dict(record))
        self._save(data)

    def getLatestRecord(self, patient_id: str) -> FabricRecord:
        data = self._load()
        history = data.get("patients", {}).get(patient_id)
        if not history:
            raise ValueError("patient not found")
        return self._from_dict(history[-1])

    def getHistory(self, patient_id: str) -> list[FabricRecord]:
        data = self._load()
        history = data.get("patients", {}).get(patient_id, [])
        return [self._from_dict(r) for r in history]

    def appendAuditLog(self, patient_id: str, audit_entry: dict[str, Any]) -> None:
        rec = self.getLatestRecord(patient_id)
        rec.audit_logs.append(audit_entry)
        self.updateRecord(rec)

    def _to_dict(self, record: FabricRecord) -> dict[str, Any]:
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

    def _from_dict(self, d: dict[str, Any]) -> FabricRecord:
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


def now_ts() -> float:
    return time.time()
