from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected marker not found in {path}: {old[:120]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Custom/reusable deployments may define optical_routes as a simple inline vocabulary
# without route-family `covers` metadata. Mapping completeness remains mandatory, but
# route compatibility can only be enforced when the vocabulary actually defines it.
replace_once(
    "scripts/validation/instrument.py",
    '''            route_term = vocabulary.get_term('optical_routes', route_type) if route_type else None
            route_covers: set[str] = set()
            if route_term is not None and isinstance(route_term.metadata, dict):
                cover_map = route_term.metadata.get('covers')
                if isinstance(cover_map, dict):
                    route_covers = {
                        str(value).strip()
                        for value in (cover_map.get(axis) or [])
                        if isinstance(value, str) and value.strip()
                    }
''',
    '''            route_term = vocabulary.get_term('optical_routes', route_type) if route_type else None
            route_covers: set[str] | None = None
            if route_term is not None and isinstance(route_term.metadata, dict):
                cover_map = route_term.metadata.get('covers')
                if isinstance(cover_map, dict):
                    route_covers = {
                        str(value).strip()
                        for value in (cover_map.get(axis) or [])
                        if isinstance(value, str) and value.strip()
                    }
''',
)
replace_once(
    "scripts/validation/instrument.py",
    '''            for method in sorted(authored - route_covers):
                issues.append(ValidationIssue(
                    code='light_path_method_route_incompatible',
                    path=f"{instrument_file.as_posix()}:light_paths[{index}].{axis}",
                    message=(
                        f"Method '{method}' is explicitly mapped to route_type '{route_type}', but that "
                        "route family does not cover the method according to vocab/optical_routes.yaml."
                    ),
                ))
''',
    '''            if route_covers is not None:
                for method in sorted(authored - route_covers):
                    issues.append(ValidationIssue(
                        code='light_path_method_route_incompatible',
                        path=f"{instrument_file.as_posix()}:light_paths[{index}].{axis}",
                        message=(
                            f"Method '{method}' is explicitly mapped to route_type '{route_type}', but that "
                            "route family does not cover the method according to the optical-route vocabulary."
                        ),
                    ))
''',
)

# Update the validator unit test to exercise the explicit mapping contract instead of
# the legacy route_type-implies-method behavior.
replace_once(
    "tests/test_validate_instrument_policy.py",
    "'optical_routes': {'source': 'inline', 'allowed_values': ['confocal_point']},",
    "'optical_routes': {'source': 'inline', 'allowed_values': ['confocal_point', 'transmitted_light']},",
)
replace_once(
    "tests/test_validate_instrument_policy.py",
    '''                        {'path': 'light_paths[].route_type', 'status': 'optional', 'type': 'string', 'vocab': 'optical_routes'},
                        {'path': 'light_paths[].readouts', 'status': 'optional', 'type': 'list', 'item_type': 'string', 'vocab': 'measurement_readouts'},
''',
    '''                        {'path': 'light_paths[].route_type', 'status': 'optional', 'type': 'string', 'vocab': 'optical_routes'},
                        {'path': 'light_paths[].imaging_modes', 'status': 'optional', 'type': 'list', 'item_type': 'string', 'vocab': 'imaging_modes'},
                        {'path': 'light_paths[].contrast_methods', 'status': 'optional', 'type': 'list', 'item_type': 'string', 'vocab': 'contrast_methods'},
                        {'path': 'light_paths[].readouts', 'status': 'optional', 'type': 'list', 'item_type': 'string', 'vocab': 'measurement_readouts'},
''',
)
replace_once(
    "tests/test_validate_instrument_policy.py",
    '''            'light_paths': [{
                'id': 'confocal_spectral_flim_fcs',
                'route_type': 'confocal_point',
                'readouts': ['spectral_imaging', 'flim'],
                'illumination_sequence': [],
                'detection_sequence': [],
            }],
''',
    '''            'light_paths': [{
                'id': 'confocal_spectral_flim_fcs',
                'route_type': 'confocal_point',
                'imaging_modes': ['confocal_point'],
                'readouts': ['spectral_imaging', 'flim'],
                'illumination_sequence': [],
                'detection_sequence': [],
            }, {
                'id': 'transmitted_light',
                'route_type': 'transmitted_light',
                'contrast_methods': ['transmitted_brightfield'],
                'illumination_sequence': [],
                'detection_sequence': [],
            }],
''',
)

# Reusable synthetic facility fixtures must satisfy the same authored data contract
# as production facilities. This proves downstream portability rather than exempting it.
replace_once(
    "tests/fixtures/example_facility/instruments/Example Point-Scanning Confocal.yaml",
    '''  route_type: confocal_point
''',
    '''  route_type: confocal_point
  imaging_modes:
  - confocal_point
''',
)
replace_once(
    "tests/fixtures/example_facility/instruments/Example Widefield One.yaml",
    '''  route_type: widefield_fluorescence
- id: transmitted_light
''',
    '''  route_type: widefield_fluorescence
  imaging_modes:
  - widefield_fluorescence
- id: transmitted_light
''',
)
replace_once(
    "tests/fixtures/example_facility/instruments/Example Widefield One.yaml",
    '''  route_type: transmitted_light
''',
    '''  route_type: transmitted_light
  contrast_methods:
  - transmitted_brightfield
''',
)

# Remove one-shot migration machinery from the committed tree.
for path in (
    ROOT / "scripts/_tmp_fix_method_mapping_regressions.py",
    ROOT / ".github/workflows/tmp-fix-method-mapping-regressions.yml",
):
    if path.exists():
        path.unlink()
