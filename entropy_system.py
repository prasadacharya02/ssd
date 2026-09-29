"""Legacy compatibility facade for the canonical pipeline runner.

The original all-in-one implementation duplicated monitoring, AI, response,
and blockchain orchestration. New code should use
``monitoring.pipeline_runner.PipelineRunner`` directly.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "entropy_system is legacy; use monitoring.pipeline_runner.PipelineRunner",
    DeprecationWarning,
    stacklevel=2,
)


class EntropySystem:
    """Backward-compatible facade around the canonical pipeline runner."""

    def __init__(self):
        from monitoring.pipeline_runner import PipelineRunner

        self.runner = PipelineRunner()

    def start(self):
        return self.runner.start()

    def stop(self):
        return self.runner.stop()

    def print_stats(self):
        return self.runner.print_stats()


def import_components():
    """Retained for callers of the old entry point; imports are now lazy."""
    return None


if __name__ == "__main__":
    system = EntropySystem()
    system.start()
    try:
        import time

        while True:
            time.sleep(30)
            system.print_stats()
    except KeyboardInterrupt:
        system.stop()
