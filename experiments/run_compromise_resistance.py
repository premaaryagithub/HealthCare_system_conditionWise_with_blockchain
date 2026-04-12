import csv
import time
import sys
import argparse
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from trusted_authority_service.policy import priority_to_threshold
from patient_data import generate_patient_documents
from disease_mapper import DiseaseCodeMapper


def run(
    out_csv: Path,
    n_peers: int = 5,
    *,
    mode: str = "single",
    n_docs: int = 50,
    seed: int = 7,
) -> None:
    rows: list[dict] = []
    mapper = DiseaseCodeMapper()

    def _emit_rows(*, prio: str, patient_name: str | None, disease: str | None, record_key: str | None) -> None:
        k = int(priority_to_threshold(prio))
        for compromised in range(0, n_peers + 1):
            attacker_can_decrypt = compromised >= k
            rows.append(
                {
                    "mode": mode,
                    "patient_name": patient_name or "",
                    "disease": disease or "",
                    "priority": prio,
                    "record_key": record_key or "",
                    "n_peers": n_peers,
                    "threshold_k": k,
                    "compromised_peers_c": compromised,
                    "attacker_can_reconstruct": attacker_can_decrypt,
                }
            )

    if (mode or "").strip().lower() == "single":
        priorities = ["LOW", "MEDIUM", "HIGH"]
        print(f"[compromise_resistance] mode=single priorities={priorities} n_peers={n_peers}")
        for prio in priorities:
            _emit_rows(prio=prio, patient_name=None, disease=None, record_key=None)
    elif (mode or "").strip().lower() == "patient_docs":
        print(f"[compromise_resistance] mode=patient_docs n_docs={n_docs} n_peers={n_peers}")
        docs = generate_patient_documents(n_docs, seed=seed, start_patient_number=21)
        for d in docs:
            dc = mapper.ensure_disease(d.disease)
            record_key = mapper.make_standard_record_key(d.patient_number, d.disease)
            print(
                f"[doc] name={d.patient_name} disease={dc.disease} prio={d.priority} code={record_key} legacy={dc.legacy_code or ''}"
            )
            _emit_rows(prio=d.priority, patient_name=d.patient_name, disease=dc.disease, record_key=record_key)
    else:
        raise ValueError("invalid mode (expected: single | patient_docs)")

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote: {out_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compromise-resistance evaluation (k-of-n security vs compromised peers).")
    parser.add_argument("--n-peers", type=int, default=5)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--mode", default="single", choices=["single", "patient_docs"], help="Execution mode")
    parser.add_argument("--n-docs", type=int, default=50, help="Number of patient documents (mode=patient_docs)")
    args = parser.parse_args()

    base = Path(__file__).resolve().parents[1]
    out = base / "runtime_experiments" / "compromise_resistance_results.csv"
    run(out_csv=out, n_peers=args.n_peers, mode=args.mode, n_docs=args.n_docs, seed=args.seed)
