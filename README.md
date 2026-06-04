<div align="center">

# 🏥 HealthGuard — Condition-Aware Healthcare Record System on Blockchain

**Final Year B.Tech Project · IIIT Kottayam · Computer Science & Engineering (Cyber Security)**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Hyperledger Fabric](https://img.shields.io/badge/Hyperledger_Fabric-2.x-2F3134?style=flat-square&logo=hyperledger&logoColor=white)](https://hyperledger.org/use/fabric)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-AI_Triage-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)

> A privacy-preserving, tamper-proof healthcare record system that dynamically adjusts access control thresholds based on patient condition severity — using AES-256-GCM encryption, Shamir's Secret Sharing, Hyperledger Fabric, and an LLM-driven medical triage agent.

</div>

---

## 📖 What Is This?

This is my B.Tech capstone project. The core idea is simple but the execution is not:

**The sicker a patient is, the harder it should be to access their data.**

Traditional healthcare systems use static access controls — everyone with a "Doctor" role can read everything. This system makes access dynamic. When a patient record is uploaded, a Gemini-powered triage agent reads the document and classifies the condition as `HIGH`, `MEDIUM`, or `LOW` priority. That classification directly determines how many trusted peers must cooperate to decrypt the record — enforcing a **condition-aware threshold**.

| Priority | Medical Meaning | Peers Required to Decrypt |
|---|---|---|
| `HIGH` | Critical / Life-threatening | 2 out of N |
| `MEDIUM` | Urgent, needs prompt care | 3 out of N |
| `LOW` | Routine / Non-critical | 4 out of N |

> 🔒 Note the inverse relationship: critical records require **fewer** peers because faster emergency access is critical. Routine records require **more** peers because they're accessed less urgently and benefit from stronger consensus.

---

## ✨ Key Features

- **LLM-Driven Triage** — Gemini 2.5 Flash reads uploaded patient files (PDFs, reports, prescriptions) and classifies condition severity. Threshold is set automatically — no manual configuration.
- **AES-256-GCM Encryption** — Every patient record is encrypted with a fresh per-document key (PDK). The nonce is prepended to the ciphertext. AAD (`patient_id:version`) binds the ciphertext to the record, preventing ciphertext transplant attacks.
- **Shamir's Secret Sharing (custom implementation)** — The PDK is split into `n` shares across peer nodes. Any `k` shares reconstruct the key via Lagrange interpolation over secp256k1's prime field. No single peer can decrypt alone.
- **Node Master Key (NMK) Wrapping** — Each share is additionally AES-GCM encrypted under the peer's own NMK before being stored on-chain. Shares at rest are always double-encrypted.
- **Priority Monotonicity** — Priority can only increase over a patient's lifetime. If an updated record scores lower than the existing priority, the existing priority is preserved.
- **Hyperledger Fabric Ledger** — Record metadata (encrypted file path, hash, wrapped shares, audit logs) lives on-chain. Provides immutability and tamper-evidence.
- **Audit Logging** — Every CREATE, UPDATE, and READ event is appended to the on-chain record with timestamp and requester identity.
- **Mock & Live Modes** — Full mock adapter (JSON-based ledger) for local development. Switches to the real Fabric REST gateway via env variable.
- **Streamlit Dashboard** — Simple UI for uploading records, reconstructing them, and viewing audit history.
- **Experiment Suite** — Scripts measuring latency breakdown, fault tolerance, and compromise resistance with CSV output.

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         HealthGuard System                               │
│                                                                          │
│  ┌─────────────┐     ┌──────────────────┐     ┌───────────────────────┐ │
│  │  Streamlit  │────▶│  FastAPI (TA)    │────▶│  Gemini 2.5 Flash     │ │
│  │  Dashboard  │     │  trusted_auth..  │     │  triage_agent.py      │ │
│  └─────────────┘     └────────┬─────────┘     └───────────────────────┘ │
│                               │                                          │
│              ┌────────────────┼─────────────────────┐                   │
│              ▼                ▼                      ▼                   │
│  ┌──────────────────┐  ┌────────────┐  ┌──────────────────────────────┐ │
│  │  AES-256-GCM     │  │  Shamir's  │  │  Hyperledger Fabric          │ │
│  │  Encryption      │  │  Secret    │  │  (or Mock JSON Ledger)       │ │
│  │  crypto/aes_gcm  │  │  Sharing   │  │  fabric_adapter/             │ │
│  └──────────────────┘  │  crypto/   │  └──────────────────────────────┘ │
│                        │  shamir.py │                                    │
│                        └─────┬──────┘                                   │
│                              │ split into n shares                       │
│              ┌───────────────┼───────────────┐                          │
│              ▼               ▼               ▼                          │
│         ┌────────┐      ┌────────┐      ┌────────┐                      │
│         │ Peer 1 │      │ Peer 2 │      │ Peer N │  (NMK-wrapped)       │
│         │ .key   │      │ .key   │      │ .key   │                      │
│         └────────┘      └────────┘      └────────┘                      │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Object Store (encrypted blobs)  │  Fabric Gateway (Node.js)    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
HealthCare_system_conditionWise_with_blockchain/
│
├── crypto/                         # Cryptographic primitives
│   ├── aes_gcm.py                  # AES-256-GCM encrypt/decrypt
│   └── shamir.py                   # Shamir's Secret Sharing over secp256k1 prime
│
├── trusted_authority_service/      # Core backend (FastAPI)
│   ├── app.py                      # REST API (login, upload, reconstruct, history)
│   ├── ta_core.py                  # TrustedAuthorityCore — orchestrates everything
│   ├── policy.py                   # priority → threshold mapping
│   ├── llm_adapter.py              # Bridges ta_core ↔ Gemini triage agent
│   └── auth.py                     # JWT auth, role-based access
│
├── LLM/
│   └── backend/
│       ├── triage_agent.py         # Gemini 2.5 Flash — reads files, returns JSON
│       ├── main.py                 # FastAPI bulk-analyze endpoint
│       └── config.py               # Loads GEMINI_API_KEY from .env
│
├── fabric_adapter/                 # Blockchain abstraction layer
│   ├── models.py                   # FabricRecord dataclass
│   ├── mock_fabric.py              # JSON-file mock ledger (for local dev)
│   └── rest_fabric.py              # Real Hyperledger Fabric REST adapter
│
├── peer_nodes/
│   └── peer_nmk.py                 # Per-peer Node Master Key store (AES-GCM wrap/unwrap)
│
├── storage/
│   └── object_store.py             # Local encrypted blob storage
│
├── chaincode/
│   └── healthcare/                 # Hyperledger Fabric chaincode (Node.js)
│       └── index.js
│
├── fabric-gateway-service/         # Node.js gateway to Hyperledger Fabric peer
│   └── index.js
│
├── ui_dashboard/
│   └── app.py                      # Streamlit web dashboard
│
├── experiments/                    # Benchmarking & evaluation scripts
│   ├── run_latency_breakdown.py    # End-to-end latency measurement (CSV output)
│   ├── run_fault_tolerance.py      # Peer failure simulation
│   └── run_compromise_resistance.py
│
├── data/
│   ├── disease_code_map.json       # ICD-like disease code → condition mapping
│   └── sample_patient_dataset.json
│
├── demo.py                         # Standalone demo (no server needed)
├── disease_mapper.py               # Disease code lookup utility
├── patient_data.py                 # Patient document generator (for experiments)
└── requirements.txt
```

---

## 🔐 Deep Dive: How Encryption Works

### Upload Flow

```
Patient file (bytes)
        │
        ▼
[LLM Triage Agent]
  → Gemini reads the file
  → Returns JSON: { seriousness, score, reason }
  → Maps to priority: HIGH / MEDIUM / LOW
        │
        ▼
[Priority Monotonicity Check]
  → If new priority < existing priority → keep existing
        │
        ▼
[AES-256-GCM Encryption]
  pdk = os.urandom(32)              # fresh 256-bit per-document key
  aad = f"{patient_id}:{version}"   # authenticated associated data
  nonce = os.urandom(12)            # random 96-bit nonce
  ciphertext = AESGCM(pdk).encrypt(nonce, file_bytes, aad)
  blob = nonce + ciphertext         # stored together
        │
        ▼
[Shamir Split]
  threshold = priority_to_threshold(priority)
  shares = split_secret(pdk, n=num_peers, k=threshold)
  # Polynomial over secp256k1's prime field
  # x-coordinates: 1..n, secret is f(0)
        │
        ▼
[NMK Wrap per Peer]
  for each peer:
    wrapped = AESGCM(peer_nmk).encrypt(nonce', share, aad)
    # Each share encrypted under that peer's unique NMK
        │
        ▼
[Fabric Record Written]
  { patient_id, priority, threshold, version,
    encrypted_file_path, encrypted_file_hash,
    shares_wrapped: { peer1: "...", peer2: "...", ... },
    audit_logs: [...] }
```

### Reconstruct Flow

```
[Fetch Fabric Record]
  → Get latest version, threshold, shares_wrapped
        │
        ▼
[Collect k Shares from Available Peers]
  for each peer (until k shares collected):
    share = AESGCM(peer_nmk).decrypt(wrapped_share, aad)
        │
        ▼
[Shamir Reconstruct]
  pdk = reconstruct_secret(shares)
  # Lagrange interpolation over the prime field
        │
        ▼
[AES-256-GCM Decrypt]
  Verify: hash(blob) == stored_hash   # tamper check
  nonce = blob[:12]
  plaintext = AESGCM(pdk).decrypt(nonce, ciphertext, aad)
        │
        ▼
[Append Audit Log & Return plaintext]
```

### Why AAD Matters

The `aad = f"{patient_id}:{version}"` binds the ciphertext to its exact version. If an attacker replaces `blob` for version 3 with the blob from version 1, decryption fails at the AEAD tag check — even if both use the same patient's key. This prevents **version rollback attacks**.

---

## 🧮 Shamir's Secret Sharing — Implementation Notes

The implementation lives in `crypto/shamir.py` and is built from scratch over the **secp256k1 prime field**:

```
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
```

Key design choices:
- Polynomial coefficients are generated using `secrets.randbelow(P)` — cryptographically secure
- Modular inverse uses Fermat's little theorem: `pow(a, P-2, P)` (since P is prime)
- Each share is `33 bytes`: 1-byte x-coordinate + 32-byte y-value
- Reconstruction uses Lagrange interpolation; no external library used

```python
# Split: evaluates a degree-(k-1) polynomial at x = 1..n
coeffs = [secret] + [secrets.randbelow(P) for _ in range(k - 1)]
shares = [bytes([x]) + eval_poly(coeffs, x, P).to_bytes(32, 'big') for x in range(1, n+1)]

# Reconstruct: Lagrange interpolation over F_P
# secret = Σ y_i * Π (x_j / (x_i - x_j)) mod P
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Fabric gateway and chaincode)
- A Gemini API key (`gemini-2.5-flash`)
- (Optional) Hyperledger Fabric network for production mode

### 1. Clone & Install

```bash
git clone https://github.com/premaaryagithub/HealthCare_system_conditionWise_with_blockchain.git
cd HealthCare_system_conditionWise_with_blockchain

# Python dependencies
pip install -r requirements.txt

# LLM backend dependencies
pip install -r LLM/backend/requirements.txt

# Fabric gateway (optional)
cd fabric-gateway-service && npm install && cd ..
```

### 2. Configure Environment

Create a `.env` file in the root:

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# FastAPI server
SECRET_KEY=your_jwt_secret_key
TA_NUM_PEERS=5               # number of peer nodes (default: 5)

# Fabric mode: "mock" (default) or "fabric" (live Hyperledger)
FABRIC_MODE=mock

# For live Fabric mode only:
# FABRIC_REST_URL=http://localhost:8800
# FABRIC_MSP_ID=Org1MSP
# FABRIC_CRYPTO_PATH=/path/to/crypto-config
# FABRIC_TLS_CERT_PATH=/path/to/tls/cert.pem

# Optional: bypass LLM during testing
# MOCK_LLM_PRIORITY=HIGH
```

Create a `.env` in `LLM/backend/`:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Run the Quick Demo (No Server Needed)

```bash
python demo.py
```

This runs a complete upload → reconstruct → update cycle using the mock ledger. You'll see:
- Priority assigned by mock LLM
- Threshold set automatically
- Old shares correctly failing to decrypt newer ciphertext (forward secrecy check)

### 4. Start the Trusted Authority API

```bash
cd oj_project   # from repo root
uvicorn trusted_authority_service.app:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`.

### 5. Start the Dashboard

```bash
streamlit run ui_dashboard/app.py
```

Set `TA_API_BASE_URL=http://localhost:8000` if running on a different host.

### 6. Start the LLM Triage Service (Standalone)

```bash
cd LLM/backend
uvicorn main:app --reload --port 8001
```

POST to `/bulk-analyze` with multipart files to get Gemini triage results directly.

---

## 🔌 REST API Reference

All endpoints (except `/login`) require `Authorization: Bearer <token>`.

| Method | Endpoint | Role | Description |
|---|---|---|---|
| `POST` | `/login` | — | Get JWT access token |
| `POST` | `/upload/{patient_id}` | `admin` | Upload a new patient record |
| `POST` | `/update/{patient_id}` | `admin` | Update existing record (version++) |
| `GET` | `/reconstruct/{patient_id}` | `doctor` | Decrypt and retrieve latest record |
| `GET` | `/history/{patient_id}` | `doctor` | View all record versions |

### Example: Upload

```bash
curl -X POST http://localhost:8000/upload/P001_diabetes \
  -H "Authorization: Bearer <token>" \
  -F "file=@patient_report.pdf"

# Response:
# { "patient_id": "P001_diabetes", "priority": "HIGH", "threshold": 2, "version": 1 }
```

---

## 🧪 Running Experiments

The `experiments/` folder contains scripts used for the project evaluation:

```bash
# Latency breakdown (fabric_get, share_unwrap, reconstruct, decrypt, total)
python experiments/run_latency_breakdown.py --n-peers 5 --repeats 30

# Fault tolerance: how many peers can go offline before reconstruction fails
python experiments/run_fault_tolerance.py --n-peers 5 --trials-per-f 50

# Compromise resistance: shows that k-1 shares reveal nothing about the secret
python experiments/run_compromise_resistance.py
```

All scripts output CSV files for analysis. Results were used in the BTP evaluation.

---

## 🛠️ Tech Stack

| Component | Technology | Why |
|---|---|---|
| Core API | FastAPI + Python 3.11 | Async, type-safe, auto-docs |
| Encryption | AES-256-GCM (`cryptography` lib) | AEAD — encryption + integrity |
| Secret Sharing | Custom Shamir over secp256k1 | No third-party crypto library needed |
| AI Triage | Gemini 2.5 Flash | Reads PDFs/docs natively, structured JSON output |
| Blockchain | Hyperledger Fabric 2.x | Permissioned, auditable, enterprise-grade |
| Chaincode | Node.js (Fabric SDK) | Fabric's native JS contract support |
| Gateway | Node.js + `@hyperledger/fabric-gateway` | gRPC to Fabric peer |
| Dashboard | Streamlit | Rapid prototyping, file upload support |
| Auth | JWT (PyJWT) + RBAC | Role-based: admin vs doctor |
| Mock Ledger | JSON file | Run and test everything without Fabric |

---

## 🔮 Future Work

- **Docker Compose setup** to spin up the full Fabric network automatically
- **Multi-organization support** — different hospitals as different Fabric orgs
- **IPFS integration** for decentralized encrypted blob storage
- **Threshold escalation UI** — doctors can request threshold override in emergencies with audit trail
- **Batch upload** with condition-wise grouping via the disease mapper

---

## 👨‍💻 About

Built as a Bachelor's Thesis Project (BTP) at **IIIT Kottayam** under the Computer Science & Engineering (Cyber Security) program. The goal was to combine blockchain's immutability guarantees with cryptographic access control, and automate the sensitivity classification using an LLM — making the system genuinely adaptive rather than rule-based.

If you're a student looking at this for reference — the `crypto/shamir.py` implementation, the `ta_core.py` orchestration logic, and the `experiments/` folder are the most educational parts to study.

---

## 📄 License

MIT — feel free to study, modify, and build on this.
