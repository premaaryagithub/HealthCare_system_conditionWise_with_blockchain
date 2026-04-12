import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiseaseCode:
    disease: str
    disease_id: int
    legacy_code: str | None = None


class DiseaseCodeMapper:
    def __init__(self, mapping_path: str | os.PathLike | None = None):
        repo_root = Path(__file__).resolve().parent
        default_path = repo_root / "data" / "disease_code_map.json"
        self.mapping_path = Path(mapping_path) if mapping_path is not None else default_path

        self._disease_to_id: dict[str, int] = {}
        self._id_to_disease: dict[int, str] = {}
        self._legacy: dict[str, str] = {}
        self._next_id = 1
        self.load()

    def load(self) -> None:
        if not self.mapping_path.exists():
            self.mapping_path.parent.mkdir(parents=True, exist_ok=True)
            self._seed_legacy_defaults()
            self.save()
            return

        data = json.loads(self.mapping_path.read_text(encoding="utf-8") or "{}")
        items = data.get("items", [])
        self._disease_to_id.clear()
        self._id_to_disease.clear()
        self._legacy = dict(data.get("legacy", {}))

        max_id = 0
        for it in items:
            disease = str(it["disease"]).strip()
            did = int(it["id"])
            if not disease:
                continue
            self._disease_to_id[disease.lower()] = did
            self._id_to_disease[did] = disease
            max_id = max(max_id, did)

        self._next_id = int(data.get("next_id") or (max_id + 1) or 1)
        if self._next_id <= max_id:
            self._next_id = max_id + 1

        if not self._legacy:
            self._seed_legacy_defaults()

    def save(self) -> None:
        self.mapping_path.parent.mkdir(parents=True, exist_ok=True)
        items = [{"disease": d, "id": i} for i, d in sorted(self._id_to_disease.items(), key=lambda x: x[0])]
        data = {"items": items, "next_id": self._next_id, "legacy": self._legacy}
        self.mapping_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _seed_legacy_defaults(self) -> None:
        self._legacy.update(
            {
                "hypertension": "HA",
                "heart attack": "HA",
                "fever": "fever",
                "diabetes": "diabetes",
                "asthma": "asthma",
                "stroke": "stroke",
            }
        )

    def ensure_disease(self, disease: str) -> DiseaseCode:
        d = (disease or "").strip()
        if not d:
            raise ValueError("disease is required")
        key = d.lower()
        if key in self._disease_to_id:
            did = self._disease_to_id[key]
        else:
            did = self._next_id
            self._next_id += 1
            self._disease_to_id[key] = did
            self._id_to_disease[did] = d
            self.save()
        return DiseaseCode(disease=self._id_to_disease[did], disease_id=did, legacy_code=self._legacy.get(key))

    def disease_to_id(self, disease: str) -> int:
        return self.ensure_disease(disease).disease_id

    def id_to_disease(self, disease_id: int) -> str:
        did = int(disease_id)
        if did not in self._id_to_disease:
            raise KeyError(f"unknown disease id: {did}")
        return self._id_to_disease[did]

    def disease_to_legacy(self, disease: str) -> str | None:
        return self._legacy.get((disease or "").strip().lower())

    def legacy_to_disease(self, legacy_code: str) -> str | None:
        c = (legacy_code or "").strip().lower()
        for d, lc in self._legacy.items():
            if str(lc).strip().lower() == c:
                return d
        return None

    def make_standard_record_key(self, patient_number: int, disease: str) -> str:
        did = self.disease_to_id(disease)
        return f"{int(patient_number)}_{did}"

    def parse_standard_record_key(self, record_key: str) -> tuple[int, int]:
        rk = (record_key or "").strip()
        if "_" not in rk:
            raise ValueError("invalid record key format")
        a, b = rk.split("_", 1)
        return int(a), int(b)
