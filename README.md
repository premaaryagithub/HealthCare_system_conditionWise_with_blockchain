# Healthcare Blockchain System — Condition-Wise Patient Data Management

A secure, multi-layer backend for managing patient medical records using **AES-256-GCM encryption**, **Shamir's Secret Sharing**, **Hyperledger Fabric** as the immutable audit ledger, and **Gemini 2.5 Flash** for LLM-driven triage that dynamically adjusts the reconstruction threshold based on medical severity.

> **Novel contribution:** Threshold adapts per record — critical patients require fewer peers for faster emergency access; routine records require more peers for stricter access control.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   Streamlit Dashboard                    │  ← ui_dashboard/
└──────────────────────┬───────────────────────────────────┘
                       │ HTTP
┌──────────────────────▼───────────────────────────────────┐
│           FastAPI REST API  (RBAC · JWT)                 │  ← trusted_authority_service/app.py
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│              Trusted Authority Core                      │  ← trusted_authority_service/ta_core.py
│   LLM Triage → Encrypt → Split → Wrap → Commit          │
└────────┬──────────────┬──────────────┬───────────────────┘
         │              │              │
┌────────▼──────┐ ┌─────▼──────┐ ┌───▼────────────────────┐
│  AES-256-GCM  │ │   Shamir   │ │   Hyperledger Fabric   │
│  crypto/      │ │   (k,n)    │ │   chaincode + gateway  │
└───────────────┘ └─────┬──────┘ └────────────────────────┘
                        │
                 ┌──────▼──────┐
                 │  NMK Store  │  ← peer_nodes/ (per-peer key wrapping)
                 └─────────────┘
```

**Data flow on upload:**
`File → LLM triage → AES-GCM encrypt → Shamir split PDK → NMK-wrap each share → commit FabricRecord`

**Data flow on read:**
`Fabric fetch → NMK-unwrap shares → Shamir reconstruct PDK → verify SHA-256 → AES-GCM decrypt`

---

## Security Properties

| Property | Mechanism |
|---|---|
| Encryption at rest | AES-256-GCM with 12-byte random nonce per record |
| Authenticated encryption | GCM tag + AAD binding (`patient_id:version`) prevents cross-record replay |
| No single point of key compromise | Shamir (k,n) — k-1 shares reveal zero information (information-theoretic) |
| Per-peer share protection | Each share AES-GCM wrapped with that peer's Node Master Key (NMK) |
| Tamper-evident audit trail | All reads/writes/updates immutably logged on Hyperledger Fabric |
| Blob integrity | SHA-256 of encrypted blob committed to chain; verified before decrypt |
| Role-based access | HOSPITAL can upload; DOCTOR can read/update; JWT-enforced |
| Dynamic access threshold | LLM severity → HIGH=2 peers, MEDIUM=3, LOW=4 (monotonically non-decreasing) |

---

## Quick Start (Mock Mode — no Fabric needed)

```bash
# 1. Clone and install
git clone https://github.com/premaaryagithub/HealthCare_system_conditionWise_with_blockchain.git
cd HealthCare_system_conditionWise_with_blockchain
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Set GEMINI_API_KEY in .env, or use mock LLM (see below)

# 3. Run the API
uvicorn trusted_authority_service.app:app --reload --port 8000

# 4. Run the dashboard (separate terminal)
streamlit run ui_dashboard/app.py
```

With mock LLM (no Gemini API key needed):
```bash
MOCK_LLM_PRIORITY=HIGH uvicorn trusted_authority_service.app:app --reload
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | — | Gemini API key for LLM triage |
| `MOCK_LLM_PRIORITY` | unset | If set (`HIGH`/`MEDIUM`/`LOW`), skips Gemini and uses this priority |
| `FABRIC_MODE` | `mock` | `mock` uses local JSON ledger; `fabric` uses real Hyperledger Fabric |
| `FABRIC_REST_URL` | `http://localhost:8800` | URL of the fabric-gateway-service (only if `FABRIC_MODE=fabric`) |
| `TA_NUM_PEERS` | `5` | Number of peer nodes for Shamir splitting |
| `TA_PEER_IDS` | unset | Comma-separated peer IDs (overrides `TA_NUM_PEERS`) |
| `TA_API_BASE_URL` | `http://127.0.0.1:8000` | Dashboard → API URL |

---

## API Endpoints

| Method | Path | Role | Description |
|---|---|---|---|
| `POST` | `/auth/login` | — | Returns JWT. Body: `{username, password}` |
| `POST` | `/records/upload` | `HOSPITAL` | Upload new patient record (multipart file + `patient_id` query param) |
| `GET` | `/records/{patient_id}` | `DOCTOR` | Decrypt and return latest record |
| `POST` | `/records/{patient_id}/update` | `DOCTOR` | Upload new version of existing record |
| `GET` | `/records/{patient_id}/history` | any | Version history and audit log |

Interactive docs at `http://localhost:8000/docs` when running.

---

## Project Structure

```
├── trusted_authority_service/   # FastAPI app, core orchestration, LLM adapter, RBAC
├── crypto/                      # AES-256-GCM and Shamir's Secret Sharing (from scratch)
├── peer_nodes/                  # Node Master Key (NMK) store — per-peer share wrapping
├── storage/                     # Encrypted binary object store (local filesystem)
├── fabric_adapter/              # MockFabricAdapter + FabricRestAdapter (same interface)
├── chaincode/healthcare/        # Hyperledger Fabric chaincode (Node.js)
├── fabric-gateway-service/      # Node.js Express bridge: REST ↔ Fabric gRPC
├── LLM/backend/                 # Gemini 2.5 Flash triage agent
├── ui_dashboard/                # Streamlit dashboard
├── experiments/                 # Fault tolerance, compromise resistance, latency breakdown
├── data/                        # Disease code map, sample patient dataset
└── runtime/                     # Runtime state (gitignored: ledger, NMK keys, object store)
```

---

## Threshold Policy

The LLM assigns a severity score which sets the Shamir reconstruction threshold `k`:

| LLM Output | Priority | Threshold `k` | Reasoning |
|---|---|---|---|
| Critical / score ≥ 3 | `HIGH` | 2 | Fewer peers needed → faster emergency access |
| Urgent / score = 2 | `MEDIUM` | 3 | Balanced access control |
| Moderate / Normal | `LOW` | 4 | Stricter quorum → tighter control on routine data |

Priority is **monotonically non-decreasing** — a patient's risk level can only escalate across versions, never drop.

---

## Running with Real Hyperledger Fabric

See [`fabric-network/README.md`](fabric-network/README.md) for network setup and [`fabric-gateway-service/README.md`](fabric-gateway-service/README.md) for the gateway service.

Once both are running, set:
```bash
FABRIC_MODE=fabric FABRIC_REST_URL=http://localhost:8800
```

---

## Experiments

Three quantitative experiments are in `experiments/`, with results in `runtime_experiments/`:

- **Fault Tolerance** — reconstruction success rate as available peers drop from n to k
- **Compromise Resistance** — validates k-1 shares yield zero PDK information
- **Latency Breakdown** — per-step timing: Fabric fetch, NMK unwrap, Shamir reconstruct, decrypt

---

## Tech Stack

Python · FastAPI · Hyperledger Fabric · Node.js · AES-256-GCM · Shamir's Secret Sharing · Gemini 2.5 Flash · Streamlit · PyJWT · cryptography · gRPC
