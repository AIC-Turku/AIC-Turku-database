"""Site rendering adapter.

CLI behavior remains anchored in scripts/dashboard_builder.py main().
This module exists for gradual extraction of template/site output concerns.
"""

from scripts.dashboard_builder import main

__all__ = ["main"]
