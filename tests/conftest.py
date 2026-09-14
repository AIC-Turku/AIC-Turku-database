"""Shared expensive integration-test fixtures."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def generated_dashboard() -> Path:
    """Build shared dashboard artifacts once for tests that only consume them."""
    subprocess.run(
        [sys.executable, "-m", "scripts.dashboard_builder", "--strict"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    return REPO_ROOT / "dashboard_docs"
