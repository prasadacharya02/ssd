"""Detection benchmark for the ENTROPY pipeline.

Runs a standardized battery of attack variants and legitimate workloads
through the *real* detection chain (EntropyAnalyzer -> make_decision)
and publishes detection rate, false-positive rate, false-quarantine
count, and detection latency as reproducible artifacts.

Usage:
    python -m benchmark            # full battery, writes docs/benchmark-report.md
"""

__version__ = "1.0"
