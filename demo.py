import os

from crypto.aes_gcm import decrypt as aes_decrypt
from crypto.shamir import reconstruct_secret
from fabric_adapter.mock_fabric import MockFabricAdapter
from peer_nodes.peer_nmk import PeerNMKStore
from storage.object_store import LocalObjectStore
from trusted_authority_service.ta_core import TrustedAuthorityCore


def main() -> None:
    base = os.path.dirname(__file__)
    runtime = os.path.join(base, "runtime_demo")
    os.makedirs(runtime, exist_ok=True)

    peer_ids = ["peer1", "peer2", "peer3", "peer4", "peer5"]
    fabric = MockFabricAdapter(os.path.join(runtime, "ledger", "ledger.json"))
    store = LocalObjectStore(os.path.join(runtime, "object_store"))
    nmk = PeerNMKStore(os.path.join(runtime, "nmks"), peer_ids=peer_ids)

    ta = TrustedAuthorityCore(fabric=fabric, store=store, nmk_store=nmk, peer_ids=peer_ids)

    patient_id = "P001"

    original = b"Patient report v1: blood pressure high"
    updated = b"Patient report v2: stabilized after medication"

    print("--- Upload ---")
    up = ta.upload_new_record(patient_id=patient_id, file_bytes=original, filename="v1.txt")
    print({"priority": up.priority, "threshold": up.threshold, "version": up.version})

    print("--- Doctor reconstruct (latest) ---")
    v = ta.reconstruct_latest(patient_id=patient_id, requester="doctor1")
    print({"version": v["version"], "priority": v["priority"], "threshold": v["threshold"]})

    print("--- Update ---")
    up2 = ta.update_record(patient_id=patient_id, new_file_bytes=updated, filename="v2.txt", requester="doctor1")
    print({"priority": up2.priority, "threshold": up2.threshold, "version": up2.version})

    latest = fabric.getLatestRecord(patient_id)
    prev = fabric.getHistory(patient_id)[-2]

    print("--- Old shares fail to decrypt NEW ciphertext ---")
    aad_new = f"{patient_id}:{latest.version}".encode("utf-8")
    blob_new = store.get(latest.encrypted_file_path)
    nonce_new = blob_new[:12]
    ct_new = blob_new[12:]

    aad_old = f"{patient_id}:{prev.version}".encode("utf-8")
    old_shares = []
    for pid in peer_ids[: prev.threshold]:
        old_shares.append(nmk.unwrap_share(pid, prev.shares_wrapped[pid], aad=aad_old))
    old_key = reconstruct_secret(old_shares)

    try:
        _ = aes_decrypt(old_key, nonce_new, ct_new, aad=aad_new)
        print("UNEXPECTED: old key decrypted new data")
    except Exception:
        print("OK: old key cannot decrypt new data")

    print("--- New shares decrypt NEW ciphertext ---")
    new_shares = []
    for pid in peer_ids[: latest.threshold]:
        new_shares.append(nmk.unwrap_share(pid, latest.shares_wrapped[pid], aad=aad_new))
    new_key = reconstruct_secret(new_shares)
    pt = aes_decrypt(new_key, nonce_new, ct_new, aad=aad_new)
    print(pt.decode("utf-8"))


if __name__ == "__main__":
    main()
