from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
INSTRUMENTS = ROOT / "instruments"


def as_list(value):
    return value if isinstance(value, list) else []

for path in sorted(INSTRUMENTS.glob("*.yaml")):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        continue
    caps = data.get("capabilities") if isinstance(data.get("capabilities"), dict) else {}
    modes = [str(v) for v in as_list(caps.get("imaging_modes")) if v]
    contrast = [str(v) for v in as_list(caps.get("contrast_methods")) if v]
    readouts = [str(v) for v in as_list(caps.get("readouts")) if v]
    paths = [lp for lp in as_list(data.get("light_paths")) if isinstance(lp, dict)]
    if not paths:
        continue

    mapped_modes = set()
    mapped_contrast = set()
    print(f"\n## {path.name}")
    print(f"CAP imaging_modes={modes}")
    print(f"CAP contrast_methods={contrast}")
    print(f"CAP readouts={readouts}")
    for idx, lp in enumerate(paths):
        lp_modes = [str(v) for v in as_list(lp.get("imaging_modes")) if v]
        lp_contrast = [str(v) for v in as_list(lp.get("contrast_methods")) if v]
        lp_readouts = [str(v) for v in as_list(lp.get("readouts")) if v]
        mapped_modes.update(lp_modes)
        mapped_contrast.update(lp_contrast)
        print(
            f"PATH {idx}: id={lp.get('id')!r} route_type={lp.get('route_type')!r} "
            f"imaging_modes={lp_modes} contrast_methods={lp_contrast} readouts={lp_readouts}"
        )

    missing_modes = [v for v in modes if v not in mapped_modes]
    missing_contrast = [v for v in contrast if v not in mapped_contrast]
    if missing_modes:
        print(f"UNMAPPED imaging_modes={missing_modes}")
    if missing_contrast:
        print(f"UNMAPPED contrast_methods={missing_contrast}")

    if len(paths) == 1:
        if missing_modes:
            print(f"SAFE(single-path) imaging_modes -> path 0: {missing_modes}")
        if missing_contrast:
            print(f"SAFE(single-path) contrast_methods -> path 0: {missing_contrast}")

    for mode in missing_modes:
        matches = []
        for idx, lp in enumerate(paths):
            if mode in {str(lp.get('id') or ''), str(lp.get('route_type') or '')}:
                matches.append(idx)
        if len(matches) == 1:
            print(f"SAFE(exact-route) imaging_mode {mode} -> path {matches[0]}")

print("\nAUDIT_COMPLETE")
