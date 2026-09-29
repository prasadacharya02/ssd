"""Documented Ganache deployment helper for ThreatLogger.

This script does not deploy automatically. It prints the steps required to
restrict writers to a single Ganache account and to record that address in
``.env``.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "blockchain" / "contracts" / "ThreatLogger.sol"


def main() -> int:
    print("ENTROPY ThreatLogger deployment")
    print(f"Contract source: {CONTRACT}")
    print()
    print("1. Start Ganache on ENTROPY_GANACHE_URL (default http://127.0.0.1:7545).")
    print("2. Compile blockchain/contracts/ThreatLogger.sol with solc 0.8.x.")
    print("3. Deploy from a single account; that account becomes owner.")
    print("4. Set ENTROPY_CONTRACT_ADDRESS and ENTROPY_WALLET_ADDRESS in .env.")
    print("5. Only the owner may call logThreat (onlyOwner modifier).")
    print()
    print("Without Ganache the app uses the labelled SQLite ledger fallback.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
