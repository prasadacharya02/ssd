"""Shared ransomware-family catalog for the attacker, victim, and dashboard."""

from __future__ import annotations

FAMILIES: tuple[dict, ...] = (
    {
        "id": "wannacry",
        "name": "WannaCry (2017)",
        "short_name": "WannaCry",
        "extension": ".WNCRY",
        "extensions": (".wncry", ".wncryt"),
        "note": "@Please_Read_Me@.txt",
        "note_markers": ("@please_read_me@",),
        "speed": "10-50 files/sec",
        "style": "Fast full-file simulation",
    },
    {
        "id": "ryuk",
        "name": "Ryuk (2019)",
        "short_name": "Ryuk",
        "extension": ".ryk",
        "extensions": (".ryk",),
        "note": "RyukReadMe.html",
        "note_markers": ("ryukreadme",),
        "speed": "2-5 files/sec",
        "style": "Slow selective simulation",
    },
    {
        "id": "maze",
        "name": "Maze (2020)",
        "short_name": "Maze",
        "extension": ".maze",
        "extensions": (".maze",),
        "note": "MAZE-README.txt",
        "note_markers": ("maze-readme",),
        "speed": "Moderate",
        "style": "Fixed extension simulation",
    },
    {
        "id": "revil",
        "name": "REvil (2021)",
        "short_name": "REvil",
        "extension": ".revil",
        "extensions": (".revil",),
        "note": "REVIL-README.txt",
        "note_markers": ("revil-readme",),
        "speed": "Fast",
        "style": "Parallel-style simulation",
    },
    {
        "id": "blackcat",
        "name": "BlackCat (2022)",
        "short_name": "BlackCat",
        "extension": ".abcd",
        "extensions": (".abcd",),
        "note": "RECOVER-blackcat-FILES.txt",
        "note_markers": ("recover-blackcat", "recover-"),
        "speed": "Fast",
        "style": "Random-extension simulation",
    },
    {
        "id": "alphv",
        "name": "ALPHV (2023)",
        "short_name": "ALPHV",
        "extension": ".alphv",
        "extensions": (".alphv",),
        "note": "RECOVER-alphv-FILES.txt",
        "note_markers": ("recover-alphv",),
        "speed": "Fast",
        "style": "Catalog training simulation",
    },
    {
        "id": "akira",
        "name": "Akira (2024)",
        "short_name": "Akira",
        "extension": ".akira",
        "extensions": (".akira",),
        "note": "AKIRA-README.txt",
        "note_markers": ("akira-readme",),
        "speed": "Moderate",
        "style": "Fixed extension simulation",
    },
    {
        "id": "cl0p",
        "name": "Cl0p (2025)",
        "short_name": "Cl0p",
        "extension": ".clop",
        "extensions": (".clop",),
        "note": "CLOP-README.txt",
        "note_markers": ("clop-readme",),
        "speed": "Selective",
        "style": "Document-style simulation",
    },
    {
        "id": "qilin",
        "name": "Qilin (2026)",
        "short_name": "Qilin",
        "extension": ".qilin",
        "extensions": (".qilin",),
        "note": "QILIN-README.txt",
        "note_markers": ("qilin-readme",),
        "speed": "Fast",
        "style": "Fixed extension simulation",
    },
    {
        "id": "lockbit5",
        "name": "LockBit 5.0",
        "short_name": "LockBit 5.0",
        "extension": ".lockbit",
        "extensions": (".lockbit",),
        "note": "Restore-My-Files.txt",
        "note_markers": ("restore-my-files",),
        "speed": "Very fast",
        "style": "High-speed simulation",
    },
)

LOCK_EXTENSIONS = frozenset(
    ext.lower() for family in FAMILIES for ext in family["extensions"]
)


def list_families() -> list[dict]:
    return [
        {
            "id": family["id"],
            "name": family["name"],
            "extension": family["extension"],
            "note": family["note"],
            "speed": family["speed"],
            "style": family["style"],
        }
        for family in FAMILIES
    ]


def family_from_filename(filename: str) -> str | None:
    name = filename.lower()
    extension = ""
    if "." in name:
        extension = "." + name.rsplit(".", 1)[-1]
    for family in FAMILIES:
        if extension in family["extensions"]:
            return family["short_name"]
        if any(marker in name for marker in family["note_markers"]):
            return family["short_name"]
    return None
