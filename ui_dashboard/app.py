import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Optional

import requests
import streamlit as st


@dataclass
class ApiResponse:
    ok: bool
    status_code: int
    data: Optional[Any] = None
    error_text: Optional[str] = None


def _api_base_url() -> str:
    return (os.getenv("TA_API_BASE_URL") or "http://127.0.0.1:8000").rstrip("/")


def _request(
    method: str,
    path: str,
    token: Optional[str] = None,
    params: Optional[dict[str, Any]] = None,
    json_body: Optional[dict[str, Any]] = None,
    files: Optional[dict[str, Any]] = None,
    timeout: int = 60,
) -> ApiResponse:
    url = f"{_api_base_url()}{path}"
    headers: dict[str, str] = {"accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        r = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_body,
            files=files,
            timeout=timeout,
        )
    except Exception as e:
        return ApiResponse(ok=False, status_code=0, error_text=str(e))

    if r.status_code >= 400:
        return ApiResponse(ok=False, status_code=r.status_code, error_text=r.text)

    if not r.text:
        return ApiResponse(ok=True, status_code=r.status_code, data=None)

    try:
        return ApiResponse(ok=True, status_code=r.status_code, data=r.json())
    except Exception:
        return ApiResponse(ok=True, status_code=r.status_code, data=r.text)


def _try_pretty_json(x: Any) -> str:
    try:
        return json.dumps(x, indent=2, ensure_ascii=False)
    except Exception:
        return str(x)


def _extract_file_b64(text: str) -> str:
    s = (text or "").strip()
    if not s:
        return ""
    if s.startswith("{"):
        try:
            obj = json.loads(s)
            if isinstance(obj, dict) and isinstance(obj.get("file_b64"), str):
                return obj["file_b64"].strip()
        except Exception:
            return s
    return s


def _b64_fix_padding(s: str) -> str:
    s2 = (s or "").strip().replace("\n", "").replace(" ", "")
    if not s2:
        return ""
    pad = (-len(s2)) % 4
    if pad:
        s2 = s2 + ("=" * pad)
    return s2


def _init_state() -> None:
    st.session_state.setdefault("hospital_token", "")
    st.session_state.setdefault("doctor_token", "")
    st.session_state.setdefault("patient_id", "1")


def _login(role: str, username: str, password: str) -> ApiResponse:
    resp = _request(
        "POST",
        "/auth/login",
        json_body={"username": username, "password": password},
    )
    if not resp.ok:
        return resp

    token = None
    if isinstance(resp.data, dict):
        token = resp.data.get("access_token")

    if not token:
        return ApiResponse(ok=False, status_code=resp.status_code, error_text=f"Unexpected login response: {resp.data}")

    if role == "hospital":
        st.session_state["hospital_token"] = token
    elif role == "doctor":
        st.session_state["doctor_token"] = token

    return resp


def _upload(patient_id: str, token: str, file_obj) -> ApiResponse:
    files = {
        "file": (file_obj.name, file_obj.getvalue(), getattr(file_obj, "type", None) or "application/octet-stream"),
    }
    return _request(
        "POST",
        "/records/upload",
        token=token,
        params={"patient_id": patient_id},
        files=files,
        timeout=120,
    )


def _view_latest(patient_id: str, token: str) -> ApiResponse:
    return _request(
        "GET",
        f"/records/{patient_id}",
        token=token,
        timeout=120,
    )


def _history(patient_id: str, token: str) -> ApiResponse:
    return _request(
        "GET",
        f"/records/{patient_id}/history",
        token=token,
        timeout=120,
    )


def _update(patient_id: str, token: str, file_obj) -> ApiResponse:
    files = {
        "file": (file_obj.name, file_obj.getvalue(), getattr(file_obj, "type", None) or "application/octet-stream"),
    }
    return _request(
        "POST",
        f"/records/{patient_id}/update",
        token=token,
        files=files,
        timeout=120,
    )


def _render_response(title: str, resp: ApiResponse) -> None:
    if resp.ok:
        st.success(f"{title} OK (HTTP {resp.status_code})")
        st.code(_try_pretty_json(resp.data), language="json")
        return

    st.error(f"{title} FAILED")
    st.write(f"HTTP: {resp.status_code}")
    if resp.error_text:
        st.code(resp.error_text)


def main() -> None:
    st.set_page_config(page_title="Healthcare TA Dashboard", page_icon="🩺", layout="wide")
    _init_state()

    st.title("Healthcare TA Dashboard")

    with st.sidebar:
        st.subheader("Connection")
        st.write(f"API Base URL: `{_api_base_url()}`")

        st.subheader("Quick Patient")
        st.session_state["patient_id"] = st.text_input("patient_id", st.session_state["patient_id"])

        st.subheader("Tokens")
        st.text_area("Hospital token", st.session_state["hospital_token"], height=110, disabled=True)
        st.text_area("Doctor token", st.session_state["doctor_token"], height=110, disabled=True)

        st.caption("Upload requires HOSPITAL token. View/Update requires DOCTOR token.")

    tab1, tab2, tab3, tab4 = st.tabs(["Login", "Upload", "View", "Update"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Hospital Login")
            h_user = st.text_input("Hospital username", value="hospital1", key="h_user")
            h_pass = st.text_input("Hospital password", value="hospital1", type="password", key="h_pass")
            if st.button("Login as Hospital"):
                resp = _login("hospital", h_user, h_pass)
                _render_response("Hospital login", resp)

        with c2:
            st.subheader("Doctor Login")
            d_user = st.text_input("Doctor username", value="doctor1", key="d_user")
            d_pass = st.text_input("Doctor password", value="doctor1", type="password", key="d_pass")
            if st.button("Login as Doctor"):
                resp = _login("doctor", d_user, d_pass)
                _render_response("Doctor login", resp)

    with tab2:
        st.subheader("Upload New Record (Hospital)")
        up_file = st.file_uploader("Choose file", type=None, key="upload_file")
        if st.button("Upload", type="primary"):
            if not st.session_state["hospital_token"]:
                st.error("Missing hospital token. Login as Hospital first.")
            elif not up_file:
                st.error("Please select a file.")
            else:
                resp = _upload(st.session_state["patient_id"], st.session_state["hospital_token"], up_file)
                _render_response("Upload", resp)

    with tab3:
        st.subheader("View Latest Record (Doctor)")
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Fetch latest", type="primary"):
                if not st.session_state["doctor_token"]:
                    st.error("Missing doctor token. Login as Doctor first.")
                else:
                    resp = _view_latest(st.session_state["patient_id"], st.session_state["doctor_token"])
                    _render_response("View", resp)

        with c2:
            if st.button("Fetch history"):
                if not st.session_state["doctor_token"] and not st.session_state["hospital_token"]:
                    st.error("Login first.")
                else:
                    tok = st.session_state["doctor_token"] or st.session_state["hospital_token"]
                    resp = _history(st.session_state["patient_id"], tok)
                    _render_response("History", resp)

        st.divider()
        st.subheader("Decode file (from View response)")
        st.caption("Paste either the full JSON response from View, or just the `file_b64` value.")
        b64_input = st.text_area("JSON or file_b64", key="file_b64")
        if st.button("Decode"):
            try:
                extracted = _extract_file_b64(b64_input)
                fixed = _b64_fix_padding(extracted)
                raw = base64.b64decode(fixed, validate=False)
                st.success(f"Decoded {len(raw)} bytes")
                try:
                    st.text(raw.decode("utf-8"))
                except Exception:
                    st.write(raw[:200])
            except Exception as e:
                st.error(str(e))

    with tab4:
        st.subheader("Update Record (Doctor)")
        upd_file = st.file_uploader("Choose updated file", type=None, key="update_file")
        if st.button("Update", type="primary"):
            if not st.session_state["doctor_token"]:
                st.error("Missing doctor token. Login as Doctor first.")
            elif not upd_file:
                st.error("Please select a file.")
            else:
                resp = _update(st.session_state["patient_id"], st.session_state["doctor_token"], upd_file)
                _render_response("Update", resp)


if __name__ == "__main__":
    main()
