# Developer Notes — Experiments Upgrade (single vs patient_docs)

## What was added

- `patient_data.py`
  - Generates **text-based** patient documents.
  - Each document contains:
    - `patient_name`
    - `disease`
    - `priority` (LOW/MEDIUM/HIGH)
    - `patient_number`

- `disease_mapper.py`
  - Maintains a **persistent** disease → numeric ID mapping.
  - Standard record key format:
    - `<patientNumber>_<diseaseId>` (e.g., `21_1`)
  - Legacy compatibility:
    - Keeps a legacy-code hint map (e.g., hypertension → `HA`) without removing old formats.

- `data/disease_code_map.json`
  - Persistent store for disease IDs and legacy mappings.

- `data/sample_patient_dataset.json`
  - Example synthetic dataset (for reference/demo). The experiments generate datasets dynamically at runtime.

## Integration points (where patient-doc mode is hooked)

- `experiments/run_fault_tolerance.py`
  - Adds `--mode single|patient_docs`
  - Adds `--n-docs`, `--seed`
  - In `patient_docs` mode:
    - generates `N` patient documents
    - maps each disease to a numeric ID
    - builds record key as `<patientNumber>_<diseaseId>`
    - runs the same fault-tolerance loop (simulate peer failures) per document

- `experiments/run_latency_breakdown.py`
  - Adds `--mode single|patient_docs`
  - Adds `--n-docs`, `--seed`
  - In `patient_docs` mode:
    - generates `N` patient documents
    - uploads each as a separate record
    - runs repeated reconstructions to capture timing breakdown

- `experiments/run_compromise_resistance.py`
  - Adds `--mode single|patient_docs`
  - Adds `--n-docs`, `--seed`
  - Computes analytic k-of-n security table using `priority_to_threshold()`.

## Output observability

- All experiments print clear markers such as:
  - `[fault_tolerance] mode=...`
  - `[latency] mode=...`
  - `[compromise_resistance] mode=...`
  - `[doc] name=... disease=... prio=... code=... legacy=...`

## Where results go

- CSV outputs are written under:
  - `runtime_experiments/`

(That folder is ignored by `.gitignore` by default.)
