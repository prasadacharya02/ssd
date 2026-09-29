"""Reset generated ENTROPY lab state.

This utility is deliberately guarded by ``--yes`` and performs no work when it
is imported. It only touches paths defined by the repository configuration.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sqlite3
import stat

import config
from victim_server.create_fake_files import restore_all_files


def _remove_tree(path: Path) -> None:
    def make_writable(_func, target, _error):
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
        _func(target)

    if path.exists():
        shutil.rmtree(path, onerror=make_writable)


def clear_events_database() -> None:
    path = Path(config.DB_PATH)
    if not path.exists():
        return
    with sqlite3.connect(path) as connection:
        table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='events'"
        ).fetchone()
        if table_exists:
            connection.execute("DELETE FROM events")
            connection.execute("DELETE FROM sqlite_sequence WHERE name='events'")


def reset_runtime_state(*, quiet: bool = False) -> dict[str, object]:
    """Clear runtime state and regenerate the controlled victim fixtures."""
    clear_events_database()

    quarantine = Path(config.QUARANTINE_DIR)
    _remove_tree(quarantine)
    quarantine.mkdir(parents=True, exist_ok=True)

    testing = Path(config.TESTING_DATA_DIR)
    _remove_tree(testing)
    testing.mkdir(parents=True, exist_ok=True)

    local_ledger = Path(config.BLOCKCHAIN_DIR) / "ledger.db"
    local_ledger.unlink(missing_ok=True)

    fixture_summary = restore_all_files(quiet=quiet)
    result = {
        "database": config.DB_PATH,
        "quarantine": str(quarantine),
        "testing": str(testing),
        "local_ledger_removed": not local_ledger.exists(),
        "fixtures": fixture_summary,
    }

    if not quiet:
        print("ENTROPY lab state reset")
        print(f"  Events DB : {config.DB_PATH}")
        print(f"  Quarantine: {quarantine}")
        print(f"  Test data : {testing}")
        print(f"  Fixtures  : {fixture_summary['files_created']} clean files")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset generated ENTROPY lab state")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="confirm deletion of generated database, quarantine, and fixture state",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if not args.yes:
        parser.error("refusing to reset without --yes")

    reset_runtime_state(quiet=args.quiet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
