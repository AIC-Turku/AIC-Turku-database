# STED instrument schema migration note

This update introduces structured STED-oriented instrument inventory fields and vocabularies.

## What changed

- Added structured light-source metadata for role/timing and pulsed-laser defaults:
  - `hardware.light_sources[].role`
  - `hardware.light_sources[].timing_mode`
  - `hardware.light_sources[].pulse_width_ps`
  - `hardware.light_sources[].repetition_rate_mhz`
  - `hardware.light_sources[].depletion_targets_nm`
- Added detector facility-default gating capability/settings:
  - `hardware.detectors[].supports_time_gating`
  - `hardware.detectors[].default_gating_delay_ns`
  - `hardware.detectors[].default_gate_width_ns`
- Added optical modulator inventory:
  - `hardware.optical_modulators[]`
  - `hardware.optical_modulators[].type`
  - `hardware.optical_modulators[].manufacturer`
  - `hardware.optical_modulators[].model`
  - `hardware.optical_modulators[].supported_phase_masks`
  - `hardware.optical_modulators[].notes`
- Added adaptive illumination logic inventory:
  - `hardware.illumination_logic[]`
  - `hardware.illumination_logic[].method`
  - `hardware.illumination_logic[].default_enabled`
  - `hardware.illumination_logic[].notes`

## Conditional requirement behavior

- `pulse_width_ps` and `repetition_rate_mhz` are conditionally required when `timing_mode` is `pulsed`.
- `depletion_targets_nm` is conditionally required when `role` is `depletion`.
- Detector default gating values are conditionally required when `supports_time_gating` is `true` and should be treated as facility defaults, not experiment-level truth.

## Validator condition extension

The validator now supports generic item-scoped conditional checks:

```yaml
required_if:
  item_field_in:
    <field_name>: [allowed_values]
```

Use this for list-item conditions instead of free-text note matching.
