# Validation warning cleanup backlog (strict build)

Source run: `python -m scripts.dashboard_builder --strict` (2026-05-02, UTC).

This issue/PR groups remaining warnings into cleanup tracks so they can be fixed in bounded follow-ups without mixing schema migration with data remediation.

## 1) Software completeness
**Current warning volume:** ~14

Scope:
- Missing `software[].version` / conditional software version metadata.
- Coverage gaps in software records across active instruments.

Representative files:
- `instruments/Abberior STED.yaml`
- `instruments/Andor BC43 Benchtop Confocal.yaml`
- `instruments/EVOS fl.yaml`
- `instruments/Lambert FLIM.yaml`
- `instruments/Leica Thunder.yaml`
- `instruments/Nikon Ti2-E Crest V3 Spinning Disk.yaml`
- `instruments/ONI Nanoimager.yaml`
- `instruments/Olympus BX60.yaml`
- `instruments/Zeiss AxioZoom V16.yaml`

Plan:
- Add explicit version fields (or policy-consistent not-applicable/unknown markers).
- Ensure all acquisition/control software rows satisfy required/conditional fields.

## 2) QC/maintenance coverage
**Current warning volume:** ~134

Scope:
- Legacy ledger entries missing newer required fields (schema version, structured reason/summary/details, setpoint metadata).
- Pattern mismatches in IDs.
- Unsupported legacy fields in maintenance entries.
- Cross-field rule warnings.

Representative paths:
- `qc/sessions/scope-3i-csu-w1-spinning-disk/**`
- `maintenance/events/scope-3i-csu-w1-spinning-disk/**`
- `maintenance/events/scope-nikon-crest-v3/**`

Plan:
- Define migration profile for historical ledgers (strict normalization vs compatibility mode).
- Backfill minimally required fields where feasible.
- Normalize ID patterns and remove unsupported fields.

## 3) Route/readout completeness
**Current warning volume:** ~14

Scope:
- Route/readout coverage and authoritative optical-route fidelity gaps.
- Non-authoritative flattened filter cube warnings (spectral model degradation risk).

Representative files:
- `instruments/Leica Thunder.yaml`
- `instruments/Nikon Eclipse Ti2-E.yaml`
- `instruments/Zeiss AxioZoom V16.yaml`

Plan:
- Replace flattened `filter_cube` shortcuts with explicit excitation/dichroic/emission components where route-level fidelity is required.
- Verify readout coverage consistency between instrument-level capabilities and route-level `light_paths[].readouts`.

## 4) Missing powers/QE/version fields
**Current warning volume:** ~12

Scope:
- Detector QE/pixel pitch/power-related completeness and similar required measurement fields.
- Conditional metadata such as module model and detector specs.

Representative files:
- `instruments/Abberior STED.yaml` (`hardware.detectors[].qe_peak_pct`)
- `instruments/Lambert FLIM.yaml` (`hardware.detectors[].pixel_pitch_um`)
- `instruments/Leica DM IRBE.yaml` (`hardware.detectors[].pixel_pitch_um`)
- `instruments/Leica DM RB.yaml` (`hardware.detectors[].pixel_pitch_um`)
- `instruments/Leica DMRE.yaml` (`hardware.detectors[].pixel_pitch_um`)
- `instruments/3i CSU-W1 Spinning Disk Med C.yaml` (`modules[].model`)

Plan:
- Fill measurable hardware metadata from manuals/vendor datasheets.
- If truly unknown, use explicit policy-compatible unknown placeholders and track as curation debt.

## 5) Remaining legacy compatibility warnings
**Current warning volume:** low (currently ~1 explicit synonym/legacy warning in strict report)

Scope:
- Alias/synonym usage and legacy compatibility paths still appearing in strict validation outputs.

Plan:
- Eliminate synonym-based values in authored YAML where canonical IDs are known.
- Keep compatibility mapping only for migration/audit tooling and mark clearly in diagnostics.

---

## Execution order (recommended)
1. Software completeness + missing QE/pixel/version fields (fast, low-risk data fixes).
2. Route/readout fidelity cleanup (optical-path authoritative quality).
3. QC/maintenance historical migration strategy and staged remediation.
4. Legacy compatibility warning burn-down to near-zero.

## Exit criteria for this cleanup epic
- Strict dashboard build warnings reduced category-by-category with tracked deltas.
- No primary production instruments missing required software/version + detector essentials.
- Route/readout warnings eliminated for active instruments in dashboard.
- Historical QC/maintenance warnings either remediated or explicitly handled in documented compatibility mode.
