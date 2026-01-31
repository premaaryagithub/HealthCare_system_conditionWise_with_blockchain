import secrets
from dataclasses import dataclass

_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F


def _mod_inv(a: int, p: int) -> int:
    return pow(a % p, p - 2, p)


def _eval_poly(coeffs: list[int], x: int, p: int) -> int:
    y = 0
    power = 1
    for c in coeffs:
        y = (y + c * power) % p
        power = (power * x) % p
    return y


def generate_secret_32() -> bytes:
    s = secrets.randbelow(_P)
    return s.to_bytes(32, byteorder="big")


def split_secret(secret: bytes, n: int, k: int) -> list[bytes]:
    if len(secret) != 32:
        raise ValueError("secret must be 32 bytes")
    if not (1 < k <= n <= 255):
        raise ValueError("invalid n/k")

    s = int.from_bytes(secret, byteorder="big")
    if s >= _P:
        raise ValueError("secret out of field")

    coeffs = [s] + [secrets.randbelow(_P) for _ in range(k - 1)]

    shares: list[bytes] = []
    for x in range(1, n + 1):
        y = _eval_poly(coeffs, x, _P)
        shares.append(bytes([x]) + y.to_bytes(32, byteorder="big"))
    return shares


def reconstruct_secret(shares: list[bytes]) -> bytes:
    if len(shares) == 0:
        raise ValueError("no shares")

    points: list[tuple[int, int]] = []
    for sh in shares:
        if len(sh) != 33:
            raise ValueError("invalid share length")
        x = sh[0]
        y = int.from_bytes(sh[1:], byteorder="big")
        points.append((x, y))

    xs = [x for x, _ in points]
    if len(set(xs)) != len(xs):
        raise ValueError("duplicate x")

    secret = 0
    for i, (x_i, y_i) in enumerate(points):
        num = 1
        den = 1
        for j, (x_j, _) in enumerate(points):
            if i == j:
                continue
            num = (num * (-x_j)) % _P
            den = (den * (x_i - x_j)) % _P
        lagrange = num * _mod_inv(den, _P)
        secret = (secret + y_i * lagrange) % _P

    return secret.to_bytes(32, byteorder="big")
