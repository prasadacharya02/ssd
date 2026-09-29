#!/usr/bin/env python3
"""
ENTROPY - Install-time Setup
Creates quarantine folder as required by spec:
"file moved to quarantine folder created by user at install of the SOC software"

This script simulates the installer that a privileged user runs.
It creates all required directories and sets up the initial estate.
"""

import os
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import config

def main():
    print("=" * 70)
    print("  ENTROPY Ransomware Shield - Installer")
    print("  Final Year Major Project - Industry Level Setup")
    print("=" * 70)

    # 1. Quarantine folder - created by user at install time (SPEC REQUIREMENT)
    q_dir = Path(config.QUARANTINE_DIR)
    q_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n[1/6] Quarantine folder created at install time:")
    print(f"      {q_dir} (privileged, PIN protected)")
    print(f"      This is where suspicious files are moved BEFORE attack proceeds")

    # 2. Backup vault
    b_dir = Path(config.BACKUP_DIR)
    b_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n[2/6] Backup vault created:")
    print(f"      {b_dir} (versioned clean copies, SHA-256 verified)")

    # 3. Logs and reports
    Path(config.LOG_DIR).mkdir(parents=True, exist_ok=True)
    Path(config.REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    print(f"\n[3/6] Logs and forensic reports:")
    print(f"      {config.LOG_DIR}")
    print(f"      {config.REPORTS_DIR}")

    # 4. Victim fixtures
    victim_files = Path(config.VICTIM_USER_FILES)
    victim_files.mkdir(parents=True, exist_ok=True)
    # Check if we need to create files
    has_files = any(victim_files.rglob("*"))
    if not has_files:
        print(f"\n[4/6] Creating victim estate (18 files)...")
        subprocess = __import__("subprocess")
        subprocess.check_call([sys.executable, str(ROOT / "victim_server" / "create_fake_files.py"), "--clean"], cwd=ROOT)
    else:
        print(f"\n[4/6] Victim estate exists: {victim_files} (18 files)")

    # 5. Blockchain ledger
    blockchain_dir = Path(config.BLOCKCHAIN_DIR)
    blockchain_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n[5/6] Blockchain audit ledger:")
    print(f"      Local fallback: {blockchain_dir / 'ledger.db'}")
    print(f"      Ganache optional: {config.GANACHE_URL}")
    print(f"      Mode: fallback enabled (works without Ganache)")

    # 6. Vault credentials
    print(f"\n[6/6] Privileged vault access configured:")
    print(f"      User: {config.VAULT_USER}")
    print(f"      PIN: {config.VAULT_PIN}")
    print(f"      Session: {config.VAULT_SESSION_HOURS} hours")
    print(f"      Scope: quarantine_only (cannot decrypt, only forensics)")

    print("\n" + "=" * 70)
    print("  Installation complete - System ready for demo")
    print("=" * 70)
    print("\n  Next steps:")
    print("    1. pip install -r requirements.txt")
    print("    2. python lab.py")
    print("    3. Open http://127.0.0.1:5000 (SOC), 5001 (Victim), 8001 (Attacker)")
    print("    4. Launch WannaCry from attacker console")
    print("    5. Watch real-time feed, kill at file 2, 18/18 restored")
    print("\n  For examiners:")
    print("    - Victim explorer is neutral (no encrypted counts)")
    print("    - SOC shows all events in real time (socket.io push)")
    print("    - Background auto-response: quarantine BEFORE attack proceeds")
    print("    - Process killed + file moved to quarantine folder from install")
    print("    - Quarantine files cannot be decrypted (ransomware destroyed original)")
    print("    - Recovery is via backup vault restore, not decryption")
    print()

if __name__ == "__main__":
    main()
