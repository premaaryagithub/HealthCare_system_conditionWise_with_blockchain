import base64
import os
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from dotenv import load_dotenv

from fabric_adapter.mock_fabric import MockFabricAdapter
from fabric_adapter.rest_fabric import FabricRestAdapter
from peer_nodes.peer_nmk import PeerNMKStore
from storage.object_store import LocalObjectStore
from trusted_authority_service.auth import authenticate, mint_token, verify_token
from trusted_authority_service.ta_core import TrustedAuthorityCore


load_dotenv()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str


class UploadResponse(BaseModel):
    patient_id: str
    priority: str
    threshold: int
    version: int


class UpdateResponse(UploadResponse):
    pass


security = HTTPBearer()


def get_user(creds: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
    try:
        return verify_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")


def require_role(role: str):
    def _dep(user=Depends(get_user)):
        if user.role != role:
            raise HTTPException(status_code=403, detail="forbidden")
        return user

    return _dep


def build_core() -> TrustedAuthorityCore:
    base = os.path.dirname(os.path.dirname(__file__))
    data_dir = os.path.join(base, "runtime")
    os.makedirs(data_dir, exist_ok=True)

    peer_ids_env = os.getenv("TA_PEER_IDS")
    if peer_ids_env:
        peer_ids = [p.strip() for p in peer_ids_env.split(",") if p.strip()]
    else:
        num_peers = int(os.getenv("TA_NUM_PEERS") or "5")
        if num_peers < 2:
            num_peers = 2
        peer_ids = [f"peer{i}" for i in range(1, num_peers + 1)]

    mode = (os.getenv("FABRIC_MODE") or "mock").lower()
    if mode == "fabric":
        fabric_rest_url = os.getenv("FABRIC_REST_URL") or "http://localhost:8800"
        fabric = FabricRestAdapter(fabric_rest_url)
    else:
        fabric = MockFabricAdapter(os.path.join(data_dir, "ledger", "ledger.json"))
    store = LocalObjectStore(os.path.join(data_dir, "object_store"))
    nmk = PeerNMKStore(os.path.join(data_dir, "nmks"), peer_ids=peer_ids)

    return TrustedAuthorityCore(fabric=fabric, store=store, nmk_store=nmk, peer_ids=peer_ids)


core = build_core()

app = FastAPI(title="Trusted Health Data Authority")


@app.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest):
    try:
        user = authenticate(req.username, req.password)
        return LoginResponse(access_token=mint_token(user))
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/records/upload", response_model=UploadResponse)
async def upload_record(
    patient_id: str,
    file: UploadFile = File(...),
    user=Depends(require_role("HOSPITAL")),
):
    try:
        b = await file.read()
        res = core.upload_new_record(patient_id=patient_id, file_bytes=b, filename=file.filename, requester=user.username)
        return UploadResponse(**res.__dict__)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/records/{patient_id}")
def view_record(patient_id: str, user=Depends(require_role("DOCTOR"))):
    try:
        return core.reconstruct_latest(patient_id=patient_id, requester=user.username)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/records/{patient_id}/update", response_model=UpdateResponse)
async def update_record(
    patient_id: str,
    file: UploadFile = File(...),
    user=Depends(require_role("DOCTOR")),
):
    try:
        b = await file.read()
        res = core.update_record(patient_id=patient_id, new_file_bytes=b, filename=file.filename, requester=user.username)
        return UpdateResponse(**res.__dict__)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/records/{patient_id}/history")
def history(patient_id: str, user=Depends(get_user)):
    try:
        return {"patient_id": patient_id, "history": core.get_history(patient_id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
