"""Streaming helpers for hashing potentially large files.

Supports SHA-256 (legacy) and SHA-3-256 (industry standard, claimed in pitch).
Both are computed without loading the whole file into memory.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


DEFAULT_CHUNK_SIZE = 1024 * 1024


def sha256_file(path: str | Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    """Return a SHA-256 digest without loading the whole file into memory."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def sha3_256_file(path: str | Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    """Return a SHA3-256 digest (NIST standard) - industry level fingerprint."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    digest = hashlib.sha3_256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def dual_hash_file(path: str | Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> dict:
    """Return both SHA-256 and SHA3-256 for maximum forensic integrity."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    sha256 = hashlib.sha256()
    sha3 = hashlib.sha3_256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            sha256.update(chunk)
            sha3.update(chunk)
    return {
        "sha256": sha256.hexdigest(),
        "sha3_256": sha3.hexdigest(),
    }


def sha256_bytes(data: bytes) -> str:
    """SHA-256 of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def sha3_256_bytes(data: bytes) -> str:
    """SHA3-256 of raw bytes."""
    return hashlib.sha3_256(data).hexdigest()
