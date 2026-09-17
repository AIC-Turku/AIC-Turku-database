"""Dashboard package.

This package separates dashboard production concerns:
- canonical/build orchestration via scripts.build_context
- repository/YAML loading via scripts.dashboard.loaders
- derived dashboard view DTOs via scripts.dashboard.instrument_view
- optical-path view DTOs via scripts.dashboard.optical_path_view
- downstream export adapters via scripts.dashboard.llm_export, methods_export, and vm_export

Import from those submodules directly; this package has no top-level exports.
"""

from __future__ import annotations
