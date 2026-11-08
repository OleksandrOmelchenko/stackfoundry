"""stackfoundry helper CLI: standard library only, no network access."""

__all__ = ["PLUGIN_ROOT", "REFERENCE"]

from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
REFERENCE = PLUGIN_ROOT / "reference"
