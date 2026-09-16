from pathlib import Path


def replace_exact(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"{path}: expected exactly one match")
    p.write_text(text.replace(old, new), encoding="utf-8")

replace_exact(
    "assets/javascripts/methods_generator_app.js",
    '            "scan zoom, pixel dwell time, line/frame averaging, and, when a confocal pinhole was used, its diameter (in Airy units)"),\n',
    '            "confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging"),\n',
)

replace_exact(
    "tests/test_software_status_semantics.py",
    'class _Vocab:\n    def resolve_canonical(self, *_args, **_kwargs):\n        return None\n',
    'class _Vocab:\n    terms_by_vocab = {}\n\n    def resolve_canonical(self, *_args, **_kwargs):\n        return None\n',
)

print("Applied test corrections")
