# Optical Contract: `selected_execution.v2`

## 1. Runtime Optical Contract

**Contract version:** `selected_execution.v2`

- **Location:** `light_paths[].selected_execution` in the DTO produced by
  `scripts/lightpath/vm_payload.py` (exported via `scripts/light_path_parser.py`
  compatibility shim).
- **Schema:**
  ```yaml
  selected_execution:
    contract_version: "selected_execution.v2"
    selected_route_steps:
      - route_step_id: "illumination-step-7"
        step_id: "illumination-step-7"        # Backward-compat alias
        route_id: "confocal_spinning_disk"
        mechanism_id: "crest_excitation_wheel"
        element_id: "crest_excitation_wheel"
        selection_state: "unresolved"          # or "resolved" or "fixed"
        selected_position_id: null             # null when unresolved
        selected_position_key: null
        selected_position_label: null
        spectral_ops: null                     # null when unresolved
        available_positions:                   # only when unresolved
          - { position_key: "Pos_1", slot: 1, label: "..." }
          - { position_key: "Pos_2", slot: 2, label: "..." }
    warnings:
  ```
- **Authority:** Python (`scripts/lightpath/*`, compatibility-exported via
  `scripts/light_path_parser.py`) is the sole author of optical meaning.
  Every `spectral_ops` value on every step is computed at parse-time.
  JavaScript may *execute* pre-computed `spectral_ops` (apply masks to
  wavelength grids for simulation/rendering) but must never *reconstruct*
  optics from raw component metadata.
- **Selection states:**
  * `"resolved"` — YAML route authored a `position_id`; fully resolved with
    `spectral_ops`.
  * `"fixed"` — Element has 0–1 positions or is not a positioned step
    (source/detector/sample/routing).
  * `"unresolved"` — Multi-position mechanism with no authored selection.
    `spectral_ops` is null; `available_positions` lists candidates.

## 2. Canonical cube component keys

Parser canonical field names for cube sub-components:

| Canonical key | Obsolete alias (no longer resolved by JS) |
|---|---|
| `excitation_filter` | `excitation`, `ex` |
| `dichroic` | `di` |
| `emission_filter` | `emission`, `em` |

Aliases are no longer resolved in `virtual_microscope_app.js` or
`virtual_microscope_runtime.js`. New YAML and DTO output must use canonical keys.

## 3. JS/Python authority boundary

- Python is the sole author of `spectral_ops` and optical meaning.
- JavaScript executes pre-computed masks and renders spectra; it does not
  reconstruct filter/cube optics from raw metadata.
- Composite cube scoring in the optimizer uses `componentMask` on the combined
  `spectral_ops` from the parser.

## 4. Compatibility notes

| Scenario | Behavior |
|---|---|
| Stale payload without canonical cube keys | Cube expansion returns no sub-components; UI falls back to composite `spectral_ops` rendering. |
| `_cube_incomplete` or `_unsupported_spectral_model` | Cube continues to receive a score of zero in the optimizer. |
| `selected_execution` present, `contract_version` absent | Audit emits a warning; contract treated as pre-v2. |
