import base64
import os
import tempfile
import time
from dataclasses import dataclass
from typing import Any

from crypto.aes_gcm import decrypt as aes_decrypt
from crypto.aes_gcm import encrypt as aes_encrypt
from crypto.shamir import reconstruct_secret, split_secret
from fabric_adapter.models import FabricRecord
from peer_nodes.peer_nmk import PeerNMKStore
from storage.object_store import LocalObjectStore
from trusted_authority_service.llm_adapter import classify_from_file
from trusted_authority_service.policy import priority_to_threshold


@dataclass
class UploadResult:
    patient_id: str
    priority: str
    threshold: int
    version: int


class TrustedAuthorityCore:
    def __init__(
        self,
        fabric: Any,
        store: LocalObjectStore,
        nmk_store: PeerNMKStore,
        peer_ids: list[str],
    ):
        self.fabric = fabric
        self.store = store
        self.nmk_store = nmk_store
        self.peer_ids = peer_ids

    def _parse_patient_and_condition(self, record_key: str) -> tuple[str, str | None]:
        rk = (record_key or "").strip()
        if "_" not in rk:
            return rk, None
        base, cond = rk.split("_", 1)
        base = base.strip()
        cond = cond.strip()
        if not base:
            base = rk
        if not cond:
            cond = None
        return base, cond

    def _priority_rank(self, priority: str) -> int:
        p = (priority or "").strip().upper()
        if p == "HIGH":
            return 3
        if p == "MEDIUM":
            return 2
        if p == "LOW":
            return 1
        return 0

    def upload_new_record(self, patient_id: str, file_bytes: bytes, filename: str, requester: str | None = None) -> UploadResult:
        try:
            latest = self.fabric.getLatestRecord(patient_id)
            version = latest.version + 1
            existing_priority = latest.priority
            existing_audit_logs = list(latest.audit_logs)
        except Exception:
            latest = None
            version = 1
            existing_priority = None
            existing_audit_logs = []

        llm_priority = self._run_llm(file_bytes, filename)
        if existing_priority is not None and self._priority_rank(llm_priority) < self._priority_rank(existing_priority):
            priority = existing_priority
        else:
            priority = llm_priority

        threshold = priority_to_threshold(priority)

        aad = f"{patient_id}:{version}".encode("utf-8")
        pdk = os.urandom(32)

        enc = aes_encrypt(pdk, file_bytes, aad=aad)
        blob = enc.nonce + enc.ciphertext

        base_patient_id, condition = self._parse_patient_and_condition(patient_id)
        path, h = self.store.put(base_patient_id, version, blob, condition=condition)

        shares = split_secret(pdk, n=len(self.peer_ids), k=threshold)
        shares_wrapped: dict[str, str] = {}
        for peer_id, share in zip(self.peer_ids, shares, strict=True):
            wrapped = self.nmk_store.wrap_share(peer_id, share, aad=aad)
            shares_wrapped[peer_id] = wrapped

        audit_logs = list(existing_audit_logs)
        audit_logs.append(
            {
                "event": "CREATE" if version == 1 else "UPDATE",
                "timestamp": time.time(),
                "requester": requester,
                "priority": priority,
                "threshold": threshold,
                "version": version,
            }
        )

        rec = FabricRecord(
            patient_id=patient_id,
            priority=priority,
            threshold=threshold,
            version=version,
            encrypted_file_path=path,
            encrypted_file_hash=h,
            shares_wrapped=shares_wrapped,
            timestamp=time.time(),
            audit_logs=audit_logs,
        )

        if version == 1:
            self.fabric.createRecord(rec)
        else:
            self.fabric.updateRecord(rec)
        return UploadResult(patient_id=patient_id, priority=priority, threshold=threshold, version=version)

    def reconstruct_latest(self, patient_id: str, requester: str) -> dict[str, Any]:
        rec = self.fabric.getLatestRecord(patient_id)
        aad = f"{patient_id}:{rec.version}".encode("utf-8")

        peer_ids = list(self.peer_ids)[: rec.threshold]
        shares: list[bytes] = []
        for peer_id in peer_ids:
            wrapped = rec.shares_wrapped[peer_id]
            shares.append(self.nmk_store.unwrap_share(peer_id, wrapped, aad=aad))

        pdk = reconstruct_secret(shares)

        blob = self.store.get(rec.encrypted_file_path)
        if self.store.hash(blob) != rec.encrypted_file_hash:
            raise ValueError("encrypted file hash mismatch")

        nonce = blob[:12]
        ciphertext = blob[12:]
        plaintext = aes_decrypt(pdk, nonce, ciphertext, aad=aad)

        audit_entry = {
            "event": "READ",
            "timestamp": time.time(),
            "requester": requester,
            "version": rec.version,
        }
        if hasattr(self.fabric, "appendAuditLog"):
            self.fabric.appendAuditLog(patient_id, audit_entry)
        else:
            rec.audit_logs.append(audit_entry)
            self.fabric.updateRecord(rec)

        return {
            "patient_id": rec.patient_id,
            "priority": rec.priority,
            "threshold": rec.threshold,
            "version": rec.version,
            "file_b64": base64.b64encode(plaintext).decode("utf-8"),
            "audit_logs": [*rec.audit_logs, audit_entry],
        }

    def update_record(self, patient_id: str, new_file_bytes: bytes, filename: str, requester: str) -> UploadResult:
        latest = self.fabric.getLatestRecord(patient_id)
        version = latest.version + 1

        llm_priority = self._run_llm(new_file_bytes, filename)
        if self._priority_rank(llm_priority) < self._priority_rank(latest.priority):
            priority = latest.priority
        else:
            priority = llm_priority
        threshold = priority_to_threshold(priority)

        aad = f"{patient_id}:{version}".encode("utf-8")
        pdk = os.urandom(32)

        enc = aes_encrypt(pdk, new_file_bytes, aad=aad)
        blob = enc.nonce + enc.ciphertext
        base_patient_id, condition = self._parse_patient_and_condition(patient_id)
        path, h = self.store.put(base_patient_id, version, blob, condition=condition)

        shares = split_secret(pdk, n=len(self.peer_ids), k=threshold)
        shares_wrapped: dict[str, str] = {}
        for peer_id, share in zip(self.peer_ids, shares, strict=True):
            wrapped = self.nmk_store.wrap_share(peer_id, share, aad=aad)
            shares_wrapped[peer_id] = wrapped

        audit_logs = list(latest.audit_logs)
        audit_logs.append(
            {
                "event": "UPDATE",
                "timestamp": time.time(),
                "requester": requester,
                "priority": priority,
                "threshold": threshold,
                "version": version,
            }
        )

        rec = FabricRecord(
            patient_id=patient_id,
            priority=priority,
            threshold=threshold,
            version=version,
            encrypted_file_path=path,
            encrypted_file_hash=h,
            shares_wrapped=shares_wrapped,
            timestamp=time.time(),
            audit_logs=audit_logs,
        )
        self.fabric.updateRecord(rec)
        return UploadResult(patient_id=patient_id, priority=priority, threshold=threshold, version=version)

    def get_history(self, patient_id: str) -> list[dict[str, Any]]:
        hist = self.fabric.getHistory(patient_id)
        return [
            {
                "patient_id": r.patient_id,
                "priority": r.priority,
                "threshold": r.threshold,
                "version": r.version,
                "timestamp": r.timestamp,
            }
            for r in hist
        ]

    def _run_llm(self, file_bytes: bytes, filename: str) -> str:
        fd, path = tempfile.mkstemp(prefix="ta_", suffix="_" + filename)
        os.close(fd)
        try:
            with open(path, "wb") as f:
                f.write(file_bytes)
            res = classify_from_file(path, filename)
            return res.priority
        finally:
            try:
                os.remove(path)
            except Exception:
                pass
