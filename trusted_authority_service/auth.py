import os
import time
from dataclasses import dataclass

import jwt


@dataclass(frozen=True)
class User:
    username: str
    role: str


_USERS = {
    "hospital1": {"password": "hospital1", "role": "HOSPITAL"},
    "doctor1": {"password": "doctor1", "role": "DOCTOR"},
}


def authenticate(username: str, password: str) -> User:
    u = _USERS.get(username)
    if not u or u["password"] != password:
        raise ValueError("invalid credentials")
    return User(username=username, role=u["role"])


def _secret() -> str:
    s = os.getenv("JWT_SECRET")
    if not s:
        raise RuntimeError("JWT_SECRET not set")
    return s


def mint_token(user: User) -> str:
    payload = {
        "sub": user.username,
        "role": user.role,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def verify_token(token: str) -> User:
    payload = jwt.decode(token, _secret(), algorithms=["HS256"])
    return User(username=payload["sub"], role=payload["role"])
