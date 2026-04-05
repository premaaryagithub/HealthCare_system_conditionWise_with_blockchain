import csv
import time
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from trusted_authority_service.policy import priority_to_threshold


def run(out_csv: Path, n_peers: int = 5) -> None:
    priorities = ["LOW", "MEDIUM", "HIGH"]

    rows = []
    for prio in priorities:
        k = int(priority_to_threshold(prio))
        for compromised in range(0, n_peers + 1):
            attacker_can_decrypt = compromised >= k
            rows.append(
                {
                    "priority": prio,
                    "n_peers": n_peers,
                    "threshold_k": k,
                    "compromised_peers_c": compromised,
                    "attacker_can_reconstruct": attacker_can_decrypt,
                }
            )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote: {out_csv}")


if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1]
    out = base / "runtime_experiments" / "compromise_resistance_results.csv"
    run(out_csv=out)
