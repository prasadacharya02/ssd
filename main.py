# main.py
# ============================================================
# ENTROPY - Environment Health Check
# ============================================================
# Single-command entry point for verifying the runtime environment.
#
# The full lab (pipeline + SOC dashboard + victim explorer + attacker
# console) is launched with `python lab.py`. This entry point only
# validates that dependencies are installed and exits non-zero when
# required packages are missing, so CI and new machines fail fast.
# ============================================================

import os
import sys
from importlib import metadata, util

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if hasattr(sys.stdout, "reconfigure") and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

__version__ = "2.0"

# Packages required for the core detection pipeline and dashboard.
REQUIRED_MODULES = (
    "watchdog",
    "psutil",
    "numpy",
    "flask",
    "flask_socketio",
    "dotenv",
)

# Optional accelerators; each has a documented fallback (rule engine,
# local SQLite ledger, plain logging).
OPTIONAL_MODULES = (
    "torch",
    "web3",
    "eventlet",
    "colorama",
)

BANNER = r"""
================================================================
                                                               
   ██████╗███╗   ██╗████████╗██████╗  ██████╗ ██████╗ ██╗   ██╗
  ██╔════╝████╗  ██║╚══██══╝██╔══██╗██╔═══██╗██╔══██╗╚██╗ ██╔╝
  █████╗  ██╔██╗ ██║   ██║   ██████╔╝██║   ██║██████╔╝ ╚████╔╝ 
  ██╔══╝  ██║╚██╗██║   ██║   ██╔══██╗██║   ██║██╔═══╝   ╚██╔╝  
  ███████╗██║ ╚████║   ██║   ██║  ██║╚██████╔╝██║        ██║   
                                                               
  Proactive Ransomware Defense System v2.0
  Environment Health Check
================================================================
"""


def _module_available(module_name: str) -> bool:
    return util.find_spec(module_name) is not None


def _app_version() -> str:
    try:
        return metadata.version("entropy-ransomware-shield")
    except Exception:
        return __version__


def main() -> int:
    print(BANNER)
    print("Environment health check")
    print("-" * 64)

    required_status = {name: _module_available(name) for name in REQUIRED_MODULES}
    optional_status = {name: _module_available(name) for name in OPTIONAL_MODULES}

    for name in REQUIRED_MODULES:
        tag = "[ OK ]" if required_status[name] else "[MISSING]"
        print(f"  {tag} required  : {name}")
    for name in OPTIONAL_MODULES:
        tag = "[ OK ]" if optional_status[name] else "[OPTIONAL]"
        print(f"  {tag} optional  : {name}")
    print("-" * 64)

    missing_required = [n for n in REQUIRED_MODULES if not required_status[n]]
    missing_optional = [n for n in OPTIONAL_MODULES if not optional_status[n]]

    if missing_required:
        print(
            "Environment incomplete — install dependencies with: "
            "pip install -r requirements-ci.txt"
        )
        return 1

    if missing_optional:
        print(
            f"{len(missing_optional)} optional package(s) unavailable "
            f"({', '.join(missing_optional)}) — using safe fallbacks"
        )

    print(f"Environment ready (version {_app_version()})")
    print("Run `python lab.py` to start the full lab.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
