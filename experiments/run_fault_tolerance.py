import csv
import os
import random
import sys
import time
import argparse
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fabric_adapter.mock_fabric import MockFabricAdapter
from fabric_adapter.rest_fabric import FabricRestAdapter
from peer_nodes.peer_nmk import PeerNMKStore
from storage.object_store import LocalObjectStore
from trusted_authority_service.ta_core import TrustedAuthorityCore
from patient_data import generate_patient_documents
from disease_mapper import DiseaseCodeMapper


def _build_ta(runtime_dir: Path, peer_ids: list[str], *, live: bool, fabric_rest_url: str | None) -> TrustedAuthorityCore:
    if live:
        base_url = (fabric_rest_url or os.getenv("FABRIC_REST_URL") or "http://127.0.0.1:8800").strip()
        fabric = FabricRestAdapter(base_url)
    else:
        fabric = MockFabricAdapter(str(runtime_dir / "ledger" / "ledger.json"))
    store = LocalObjectStore(str(runtime_dir / "object_store"))
    nmk = PeerNMKStore(str(runtime_dir / "nmks"), peer_ids=peer_ids)
    return TrustedAuthorityCore(fabric=fabric, store=store, nmk_store=nmk, peer_ids=peer_ids)


def run(
    out_csv: Path,
    n_peers: int = 5,
    trials_per_f: int = 50,
    seed: int = 7,
    patient_id: str = "P001_HA",
    live: bool = False,
    fabric_rest_url: str | None = None,
    mode: str = "single",
    n_docs: int = 50,
) -> None:
    random.seed(seed)

    base = Path(__file__).resolve().parents[1]
    runtime_dir = base / "runtime_experiments" / f"fault_tolerance_{int(time.time())}"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    peer_ids = [f"peer{i}" for i in range(1, n_peers + 1)]
    ta = _build_ta(runtime_dir, peer_ids, live=live, fabric_rest_url=fabric_rest_url)

    rows: list[dict] = []
    mapper = DiseaseCodeMapper()

    def _run_one(record_key: str, payload: bytes, *, prio: str, patient_name: str | None, disease: str | None) -> None:
        os.environ["MOCK_LLM_PRIORITY"] = prio
        up = ta.upload_new_record(patient_id=record_key, file_bytes=payload, filename="eval.txt")

        for f in range(0, n_peers + 1):
            success = 0
            for _ in range(trials_per_f):
                down = set(random.sample(peer_ids, k=f)) if f > 0 else set()
                available = [p for p in peer_ids if p not in down]
                try:
                    _ = ta.reconstruct_latest_with_peer_availability(
                        patient_id=up.patient_id,
                        requester="experiment",
                        available_peer_ids=available,
                    )
                    success += 1
                except Exception:
                    pass

            rows.append(
                {
                    "mode": mode,
                    "patient_name": patient_name or "",
                    "disease": disease or "",
                    "priority": prio,
                    "record_key": record_key,
                    "threshold_k": up.threshold,
                    "n_peers": n_peers,
                    "failed_peers_f": f,
                    "available_peers": n_peers - f,
                    "trials": trials_per_f,
                    "success": success,
                    "success_rate": success / float(trials_per_f),
                }
            )

    if (mode or "").strip().lower() == "single":
        original = b"Patient report for evaluation"
        priorities = ["LOW", "MEDIUM", "HIGH"]
        print(f"[fault_tolerance] mode=single priorities={priorities} trials={trials_per_f} n_peers={n_peers}")
        for prio in priorities:
            _run_one(patient_id + f"_{prio}", original, prio=prio, patient_name=None, disease=None)
    elif (mode or "").strip().lower() == "patient_docs":
        print(f"[fault_tolerance] mode=patient_docs n_docs={n_docs} trials={trials_per_f} n_peers={n_peers}")
        docs = generate_patient_documents(n_docs, seed=seed, start_patient_number=21)
        for d in docs:
            dc = mapper.ensure_disease(d.disease)
            record_key = mapper.make_standard_record_key(d.patient_number, d.disease)
            payload = d.to_text().encode("utf-8")
            print(
                f"[doc] name={d.patient_name} disease={dc.disease} prio={d.priority} code={record_key} legacy={dc.legacy_code or ''}"
            )
            _run_one(record_key, payload, prio=d.priority, patient_name=d.patient_name, disease=dc.disease)
    else:
        raise ValueError("invalid mode (expected: single | patient_docs)")

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote: {out_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fault-tolerance evaluation (priority vs peer failures).")
    parser.add_argument("--live", action="store_true", help="Use real Fabric via FabricRestAdapter (requires running gateway).")
    parser.add_argument(
        "--fabric-rest-url",
        default=None,
        help="Fabric gateway base URL (default: FABRIC_REST_URL env or http://127.0.0.1:8800)",
    )
    parser.add_argument("--n-peers", type=int, default=5)
    parser.add_argument("--trials", type=int, default=50, help="Trials per failure count f")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--mode", default="single", choices=["single", "patient_docs"], help="Execution mode")
    parser.add_argument("--n-docs", type=int, default=50, help="Number of patient documents (mode=patient_docs)")
    args = parser.parse_args()

    base = Path(__file__).resolve().parents[1]
    out = base / "runtime_experiments" / "fault_tolerance_results.csv"
    run(
        out_csv=out,
        n_peers=args.n_peers,
        trials_per_f=args.trials,
        seed=args.seed,
        live=bool(args.live),
        fabric_rest_url=args.fabric_rest_url,
        mode=args.mode,
        n_docs=args.n_docs,
    )
