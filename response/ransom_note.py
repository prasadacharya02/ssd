# ============================================================
# ENTROPY - Ransom Note Detection
# response/ransom_note.py
#
# A dropped ransom note is near-certain confirmation of a
# ransomware incident, independent of the entropy signals.
# Detection is two-tier:
#   1. Filename patterns — generic note names plus the exact
#      note markers from the shared family catalog (catalog.py).
#   2. Content markers — strong phrases fire on their own;
#      specific payment/encryption phrases must co-occur
#      (two or more) for a weak match, which keeps ordinary
#      documents (that may mention "backup" or "key") quiet.
# ============================================================

import os
import re

from catalog import FAMILIES

# Generic note filename patterns (lowercased basename). The prefixed
# README pattern (e.g. MAZE-README.txt, REVIL-README.txt) requires a
# prefix so that an ordinary project README.txt stays quiet.
_FILENAME_PATTERNS = [
    r"restore[-_ ]?my[-_ ]?files",
    r"please[-_ ]?read[-_ ]?me",
    r"how[-_ ]?to[-_ ]?(decrypt|recover)",
    r"decrypt[-_ ]?(instructions|now|your)",
    r"your[-_ ]?files[-_ ]?have[-_ ]?been[-_ ]?encrypted",
    r"^ransom\b",
    r"[a-z0-9]+[-_](readme|decrypt|recover)\.(txt|html?)$",
    r"read[-_ ]?me[-_ ]?now",
]

# Family-specific note markers from the shared catalog.
_FAMILY_NOTE_MARKERS = [
    marker
    for family in FAMILIES
    for marker in family.get("note_markers", ())
]

# A single occurrence is enough.
_STRONG_CONTENT_MARKERS = (
    "have been encrypted",
    "been encrypted",
    "are encrypted",
    "recover your files",
    "decrypt your files",
    "pay a ransom",
    "wallet address",
    "private key",
    "pay within",
)

# Require at least two DISTINCT phrases to avoid ordinary documents.
_WEAK_CONTENT_MARKERS = (
    "bitcoin",
    "btc",
    "dead drop",
    "your data is safe",
    "contact us at",
    "hours to pay",
    "no decryption without payment",
    "encrypted with",
    "ransom",
)

_MAX_CONTENT_SCAN_BYTES = 256 * 1024


def _filename_is_note(filename: str) -> str | None:
    name = filename.lower()
    for pattern in _FILENAME_PATTERNS:
        if re.search(pattern, name):
            return f"filename matches '{pattern}'"
    for marker in _FAMILY_NOTE_MARKERS:
        if marker in name:
            return f"filename matches known family note marker '{marker}'"
    return None


def _looks_binary(data: bytes) -> bool:
    sample = data[:4096]
    if not sample:
        return False
    suspicious = sum(
        1 for b in sample if b == 0 or (b < 9 and b not in (9, 10, 13))
    )
    return suspicious > len(sample) / 100


def detect_ransom_note(file_path: str) -> tuple[bool, list]:
    """Return (is_note, evidence) for *file_path*.

    Cheap by design: a filename check first, a bounded content scan
    only for small, readable, non-binary files.
    """
    filename = os.path.basename(file_path)

    hit = _filename_is_note(filename)
    if hit:
        return True, [hit]

    try:
        if not os.path.isfile(file_path) or \
                os.path.getsize(file_path) > _MAX_CONTENT_SCAN_BYTES:
            return False, []
        with open(file_path, "rb") as handle:
            data = handle.read()
    except OSError:
        return False, []

    if _looks_binary(data):
        return False, []

    try:
        text = data.decode("utf-8", errors="ignore").lower()
    except Exception:
        return False, []

    strong = [m for m in _STRONG_CONTENT_MARKERS if m in text]
    if strong:
        return True, [f"note content: {m!r}" for m in strong[:3]]

    weak = [m for m in _WEAK_CONTENT_MARKERS if m in text]
    if len(weak) >= 2:
        return True, [
            f"note content: {len(weak)} payment/encryption markers "
            f"({', '.join(repr(m) for m in weak[:4])})"
        ]

    return False, []
