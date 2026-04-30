# Archive: Monoliths

Files placed in this directory are **historical backups only**.

They document the state of the codebase before extraction refactors were
performed and are kept for reference and audit purposes.

## Rules

1. **Production code must never import from `archive/monoliths/`.**
   Any `import` or `from … import` statement in a production Python or
   JavaScript file that references a path inside `archive/monoliths/` is
   forbidden.

2. Archived files are read-only historical snapshots.
   Do not edit them to add new features or bug fixes.

3. If you need to compare against the archived version, read it directly;
   do not `import` it.

4. A static test (`tests/test_archive_is_not_imported.py`) enforces rule 1
   automatically on every CI run.
