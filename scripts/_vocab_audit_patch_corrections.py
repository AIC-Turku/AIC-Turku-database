from __future__ import annotations

from scripts._vocab_audit_patch_common import replace_once

replace_once(
    "scripts/lightpath/model.py",
    "import re\nfrom pathlib import Path\nfrom typing import Any\n\nfrom scripts.validation.vocabulary import Vocabulary, build_repository_vocabulary\n",
    "import re\nfrom pathlib import Path\nfrom typing import Any\n",
)
replace_once(
    "scripts/lightpath/model.py",
    "_fallback_vocab: Vocabulary | None = None\n\n\ndef _vocab_context() -> Vocabulary | VocabLookup | None:\n",
    "_fallback_vocab: Any | None = None\n\n\ndef _vocab_context() -> VocabLookup | Any | None:\n",
)
replace_once(
    "scripts/lightpath/model.py",
    """    if _fallback_vocab is None:
        _fallback_vocab = build_repository_vocabulary(Path(__file__).resolve().parents[2])
""",
    """    if _fallback_vocab is None:
        # Lazy import avoids validation -> lightpath -> validation import cycles.
        from scripts.validation.vocabulary import build_repository_vocabulary
        _fallback_vocab = build_repository_vocabulary(Path(__file__).resolve().parents[2])
""",
)

print("Applied lazy vocabulary loading correction")
