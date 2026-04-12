import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class PatientDocument:
    patient_number: int
    patient_name: str
    disease: str
    priority: str

    def to_text(self) -> str:
        return (
            f"Patient Name: {self.patient_name}\n"
            f"Patient ID: {self.patient_number}\n"
            f"Disease: {self.disease}\n"
            f"Priority: {self.priority}\n"
        )


_DEFAULT_DISEASES: dict[str, list[str]] = {
    "LOW": [
        "common cold",
        "allergic rhinitis",
        "mild fever",
        "migraine",
        "gastritis",
        "skin rash",
    ],
    "MEDIUM": [
        "diabetes",
        "asthma",
        "pneumonia",
        "hypertension",
        "kidney stones",
        "dengue",
    ],
    "HIGH": [
        "heart attack",
        "stroke",
        "sepsis",
        "respiratory failure",
        "major trauma",
        "cardiac arrest",
    ],
}

_FIRST_NAMES = [
    "Aarav",
    "Vihaan",
    "Aditya",
    "Arjun",
    "Sai",
    "Rohan",
    "Ishaan",
    "Kiran",
    "Ananya",
    "Aadhya",
    "Diya",
    "Saanvi",
    "Ira",
    "Meera",
    "Kavya",
    "Nisha",
]

_LAST_NAMES = [
    "Sharma",
    "Reddy",
    "Patel",
    "Singh",
    "Nair",
    "Iyer",
    "Gupta",
    "Kumar",
    "Das",
    "Rao",
]


def get_default_disease_dataset() -> dict[str, list[str]]:
    return {k: list(v) for k, v in _DEFAULT_DISEASES.items()}


def generate_patient_name(rng: random.Random) -> str:
    return f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"


def generate_patient_documents(
    n: int,
    *,
    seed: int = 7,
    start_patient_number: int = 100,
    diseases_by_priority: dict[str, list[str]] | None = None,
) -> list[PatientDocument]:
    rng = random.Random(seed)
    ds = diseases_by_priority or get_default_disease_dataset()

    priorities = ["LOW", "MEDIUM", "HIGH"]
    out: list[PatientDocument] = []
    for i in range(int(n)):
        prio = rng.choice(priorities)
        disease = rng.choice(ds[prio])
        out.append(
            PatientDocument(
                patient_number=start_patient_number + i,
                patient_name=generate_patient_name(rng),
                disease=disease,
                priority=prio,
            )
        )
    return out


def save_patient_dataset_json(docs: list[PatientDocument], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([asdict(d) for d in docs], indent=2), encoding="utf-8")
