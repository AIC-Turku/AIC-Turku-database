# Repository Audit

- Status: **fail**
- Errors: **42**
- Warnings: **210**

## Inventory

- Active instruments: 22
- Retired instruments: 2
- Active YAML load failures: 0
- Retired YAML load failures: 0

## Validation

- Instrument errors: 0
- Instrument warnings: 56
- Event errors: 0
- Event warnings: 130

### Most common missing required instrument-policy fields

- `instrument.location` — 7
- `hardware.optical_path_elements[].id` — 1
- `hardware.optical_path_elements[].element_type` — 1

### Most common missing conditional instrument-policy fields

- `software[].version` — 16
- `hardware.detectors[].pixel_pitch_um` — 4
- `hardware.detectors[].qe_peak_pct` — 3
- `modules[].model` — 2
- `hardware.objectives[].working_distance` — 2
- `hardware.detectors[].id` — 2
- `hardware.scanner.line_rate_hz` — 1
- `hardware.detectors[].manufacturer` — 1
- `modules[].manufacturer` — 1

### Common alias fallback paths

- `hardware.sources[].modalities` — 120
- `hardware.sources[].id` — 72
- `hardware.sources[].kind` — 48
- `hardware.detectors[].pixel_pitch_um` — 24
- `hardware.detectors[].collection_min_nm` — 24
- `hardware.detectors[].collection_max_nm` — 24
- `hardware.detectors[].collection_center_nm` — 24
- `hardware.detectors[].collection_width_nm` — 24
- `hardware.sources[].name` — 24
- `hardware.sources[].manufacturer` — 24

### Fields currently blocking trustworthy methods generation

- `software[].version` — 16
- `hardware.detectors[].pixel_pitch_um` — 4
- `modules[].model` — 2
- `hardware.optical_path_elements[].id` — 1
- `hardware.optical_path_elements[].element_type` — 1
- `hardware.scanner.line_rate_hz` — 1
- `hardware.detectors[].manufacturer` — 1
- `modules[].manufacturer` — 1

### Virtual microscope readiness

- error: 19
- ok: 2
- warning: 3

### FPbase/browser runtime contract

- Status: ok
- mCherry runtime contract passed.

### JS runtime execution authority

- Status: ok
- JS runtime authority audit passed.

### Issue categories

- scientific_support_completeness: 37
- topology_completeness: 11
- uncategorized: 18

## Highest-priority virtual microscope issues

### Nikon Ti2-E Crest V3
- ERROR: Optical component step 'detection-step-12' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-4' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-5' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-2' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-3' has no spectral_ops and no unsupported_reason.
- Warning: Light source 'D-LEDI Fluorescence LED Illumination System' has neither a fixed wavelength nor a tunable wavelength range.
- Warning: Light source 'T12-D-LHLED LED Lamp House' has neither a fixed wavelength nor a tunable wavelength range.

### Zeiss AxioZoom.V16
- ERROR: Optical component step 'detection-step-4' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-4' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-2' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-2' has no spectral_ops and no unsupported_reason.
- Warning: Light source 'CL 9000 LED CAN ring light' has neither a fixed wavelength nor a tunable wavelength range.
- Warning: Light source 'MC1000 LED base light' has neither a fixed wavelength nor a tunable wavelength range.
- Warning: Light source 'HXP 200C' has neither a fixed wavelength nor a tunable wavelength range.

### Leica STELLARIS 8
- ERROR: Virtual microscope payload splitter count mismatch: raw_total=0, payload=1.
- ERROR: Optical component step 'illumination-step-2' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-4' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-1' has no spectral_ops and no unsupported_reason.
- Warning: Light-path mechanisms exist but the payload exposes no valid_paths combinations.

### Leica DM RB
- ERROR: Optical component step 'detection-step-4' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-2' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-2' has no spectral_ops and no unsupported_reason.
- Warning: Light source '12V 100W halogen bulb' has neither a fixed wavelength nor a tunable wavelength range.
- Warning: Light source '50W HBO short arc bulb' has neither a fixed wavelength nor a tunable wavelength range.

### 3i CSU-W1 Spinning Disk
- ERROR: Optical component step 'detection-step-9' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-6' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-1' has no spectral_ops and no unsupported_reason.
- Warning: Light source 'X-Cite XLED1' has neither a fixed wavelength nor a tunable wavelength range.

### Zeiss TIRF
- ERROR: Optical component step 'detection-step-6' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-6' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-2' has no spectral_ops and no unsupported_reason.
- Warning: Light source 'Transmitted Halogen Lamp' has neither a fixed wavelength nor a tunable wavelength range.

### Leica DM IRBE
- ERROR: Optical component step 'detection-step-4' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-2' has no spectral_ops and no unsupported_reason.
- Warning: Light source '12V 100W halogen bulb' has neither a fixed wavelength nor a tunable wavelength range.
- Warning: Light source '50W HBO short arc bulb' has neither a fixed wavelength nor a tunable wavelength range.

### Olympus BX60
- ERROR: Optical component step 'detection-step-4' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-2' has no spectral_ops and no unsupported_reason.
- Warning: Light source '12V 100W halogen bulb' has neither a fixed wavelength nor a tunable wavelength range.
- Warning: Light source 'HBO 103W short arc bulb' has neither a fixed wavelength nor a tunable wavelength range.

### 3i Marianas CSU-W1 Spinning Disk Med C
- ERROR: Optical component step 'detection-step-4' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-1' has no spectral_ops and no unsupported_reason.
- Warning: Light source 'pE-300' has neither a fixed wavelength nor a tunable wavelength range.

### Nikon Eclipse Ti2-E
- ERROR: Optical component step 'detection-step-12' has no spectral_ops and no unsupported_reason.
- ERROR: Optical component step 'detection-step-2' has no spectral_ops and no unsupported_reason.
- Warning: Light source 'Ti2 Transmitted Illuminator' has neither a fixed wavelength nor a tunable wavelength range.
