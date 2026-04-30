"""Static test: production code must never import from archive/monoliths/.

Per archive/monoliths/README.md, archived files are historical backups only.
Any import of archive/monoliths content in a production Python or JavaScript
file is a policy violation.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Directories that contain production code (Python and JavaScript).
PRODUCTION_DIRS = [
    REPO_ROOT / "scripts",
    REPO_ROOT / "assets",
]

# Patterns that indicate a reference to archive/monoliths.
# We look for any of these in production source files.
_PATTERNS = [
    re.compile(r"archive[/\\]monoliths", re.IGNORECASE),
    re.compile(r"archive\.monoliths", re.IGNORECASE),
]


def _is_production_source(path: Path) -> bool:
    return path.suffix in {".py", ".js"} and path.is_file()


class ArchiveIsNotImportedTests(unittest.TestCase):
    """Fail if any production Python/JS file references archive/monoliths."""

    def test_no_production_file_imports_archive_monoliths(self) -> None:
        violations: list[str] = []

        for prod_dir in PRODUCTION_DIRS:
            if not prod_dir.exists():
                continue
            for path in prod_dir.rglob("*"):
                if not _is_production_source(path):
                    continue
                try:
                    src = path.read_text(encoding="utf-8")
                except OSError:
                    continue
                for pattern in _PATTERNS:
                    if pattern.search(src):
                        rel = path.relative_to(REPO_ROOT)
                        violations.append(str(rel))
                        break  # one violation per file is enough

        self.assertFalse(
            violations,
            "Production files must not reference archive/monoliths. "
            f"Violations found:\n" + "\n".join(f"  {v}" for v in violations),
        )


if __name__ == "__main__":
    unittest.main()
