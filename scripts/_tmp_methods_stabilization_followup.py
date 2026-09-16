from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Repair the exact-match anchor in the first temporary patcher. The production
# source comment continues on the same line with "Registered once at".
patcher = ROOT / "scripts/_tmp_apply_methods_stabilization.py"
text = patcher.read_text(encoding="utf-8")
text = text.replace(
    "// Container-level change listener for modality checkboxes.\\n''',",
    "// Container-level change listener for modality checkboxes. Registered once at\\n''',",
)
text = text.replace(
    "// Container-level change listener for modality checkboxes.\\n''',\\n)",
    "// Container-level change listener for modality checkboxes. Registered once at\\n''',\\n)",
)
patcher.write_text(text, encoding="utf-8")
