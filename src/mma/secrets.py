"""Credential encryption helpers.

On Windows this uses DPAPI scoped to the current user. MMA targets Windows first,
so this gives real at-rest protection without adding dependencies.
"""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import sys

from mma.db import Store, utc_now


class SecretError(RuntimeError):
    """Raised when secret encryption or storage fails."""


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def protect_secret(value: str) -> str:
    if sys.platform != "win32":
        raise SecretError("DPAPI secret encryption is only available on Windows")
    raw = value.encode("utf-8")
    in_buffer = ctypes.create_string_buffer(raw)
    in_blob = DATA_BLOB(len(raw), ctypes.cast(in_buffer, ctypes.POINTER(ctypes.c_char)))
    out_blob = DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    if not crypt32.CryptProtectData(
        ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
    ):
        raise SecretError("CryptProtectData failed")
    try:
        encrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        return base64.b64encode(encrypted).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def unprotect_secret(value_encrypted: str) -> str:
    if sys.platform != "win32":
        raise SecretError("DPAPI secret decryption is only available on Windows")
    raw = base64.b64decode(value_encrypted)
    in_buffer = ctypes.create_string_buffer(raw)
    in_blob = DATA_BLOB(len(raw), ctypes.cast(in_buffer, ctypes.POINTER(ctypes.c_char)))
    out_blob = DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    if not crypt32.CryptUnprotectData(
        ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
    ):
        raise SecretError("CryptUnprotectData failed")
    try:
        decrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        return decrypted.decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def store_credential(store: Store, key: str, value: str) -> None:
    encrypted = protect_secret(value)
    now = utc_now()
    with store.connect() as conn:
        conn.execute(
            """
            INSERT INTO credentials (key, value_encrypted, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value_encrypted = excluded.value_encrypted,
                updated_at = excluded.updated_at
            """,
            (key, encrypted, now, now),
        )


def load_credential(store: Store, key: str) -> str:
    with store.connect() as conn:
        row = conn.execute("SELECT value_encrypted FROM credentials WHERE key = ?", (key,)).fetchone()
    if row is None:
        raise SecretError(f"credential not found: {key}")
    return unprotect_secret(row["value_encrypted"])
