# Optical Contract Rewrite Plan

## 1. Single Authoritative Runtime Optical Contract

**Contract:** `selected_execution` (version `selected_execution.v1`)

- **Location:** `light_paths[].selected_execution` in the DTO produced by
  `light_path_parser.generate_virtual_microscope_payload()`.
- **Schema:**
  ```yaml
  selected_execution:
    contract_version: "selected_execution.v1"
    steps:              # Ordered route steps with spectral_ops
    warnings:           # Validation warnings from the parser
    illumination_traversal: [...]
    detection_traversal:    [...]
  ```
- **Authority:** Python (`light_path_parser.py`) is the sole author of optical
  meaning.  Every `spectral_ops` value on every step is computed at parse-time.
  JavaScript may *execute* pre-computed `spectral_ops` (apply masks to
  wavelength grids for simulation/rendering) but must never *reconstruct* optics
  from raw component metadata.

---

## 2. Functions Deleted

| File | Function | Reason |
|------|----------|--------|
| `virtual_microscope_runtime.js` | `expandCubeSelectionForOptimization` | Reconstructed cube sub-component optics from field aliases.  Parser pre-computes composite `spectral_ops`; optimizer now scores cubes directly via `componentMask`. |

---

## 3. Compatibility Shims Removed

| File | Location | Shim | Replacement |
|------|----------|------|-------------|
| `virtual_microscope_app.js` | `expandCubeSelection` | `cubePosition.excitation \|\| cubePosition.ex` | Canonical `cubePosition.excitation_filter` only |
| `virtual_microscope_app.js` | `expandCubeSelection` | `cubePosition.di` | Canonical `cubePosition.dichroic` only |
| `virtual_microscope_app.js` | `expandCubeSelection` | `cubePosition.emission \|\| cubePosition.em` | Canonical `cubePosition.emission_filter` only |
| `virtual_microscope_runtime.js` | (deleted function) | `component.excitation \|\| component.ex`, `component.di`, `component.emission \|\| component.em` | N/A — function deleted |

---

## 4. Data Structures That Become Obsolete

| Structure | Location | Notes |
|-----------|----------|-------|
| Legacy cube alias fields (`excitation`, `ex`, `di`, `em`) | Any DTO or payload consumer | Parser canonical keys are `excitation_filter`, `dichroic`, `emission_filter` (defined in `CUBE_LINK_KEYS`).  Aliases are no longer resolved by JS. |
| Per-sub-component expansion arrays from `expandCubeSelectionForOptimization` | Runtime optimizer | Replaced by direct composite `spectral_ops` scoring via `componentMask`. |

---

## 5. Exact Order of Implementation

1. **Create this plan document** — `docs/optical_contract_rewrite_plan.md`.
2. **Delete `expandCubeSelectionForOptimization`** in `virtual_microscope_runtime.js`
   and replace its two call-sites in `optimizeLightPath` with:
   - *Scoring:* `pointMaskScore(cubePosition, targets, mode)` on the composite
     cube (Python's `spectral_ops` handles illumination/detection phase
     separation).
   - *Selection building:* Extract sub-components using canonical field names
     (`excitation_filter`, `dichroic`, `emission_filter`) inline.
3. **Remove alias shims** from `expandCubeSelection` in
   `virtual_microscope_app.js` — keep only the canonical parser field names.
4. **Strengthen audit** in `full_audit.py`:
   - Validate `selected_execution` presence and `contract_version` on each route.
   - Validate that optical-component steps carry `spectral_ops` (or have an
     explicit `unsupported_reason`).
5. **Run targeted tests** — VM runtime, app template, contract invariants, audit.
6. **Run full test suite** — verify zero regressions.

---

## 6. Risk Notes

| Risk | Mitigation |
|------|------------|
| Old cached payloads (pre-v2) used legacy alias fields (`ex`, `di`, `em`) | Parser already emits canonical `excitation_filter`/`dichroic`/`emission_filter`.  If a stale payload lacks canonical keys the cube expansion returns no sub-components and the UI falls back to composite `spectral_ops` rendering — same as today for incomplete cubes. |
| Composite cube scoring changes optimizer ranking | Composite scoring via `componentMask` evaluates the *combined* illumination/detection transmission, which is more physically correct than separate sub-component scoring.  Scoring weights are preserved (5× excitation side, 7× emission side). |
| `_cube_incomplete` cubes lose scoring exclusion | The exclusion guard (`_cube_incomplete \|\| _unsupported_spectral_model`) is preserved inline at the call site — incomplete cubes continue to receive a score of zero. |
| Audit strictness increase may surface new warnings | New `selected_execution` validation is additive (warnings, not errors) so existing CI is unaffected until policies are tightened. |
