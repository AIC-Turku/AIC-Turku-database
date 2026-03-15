# Dichroic spectral model migration note

## Why this changed

Historically, some multiband dichroics were encoded only as:

- `component_type: multiband_dichroic`
- `cutoffs_nm: [a, b, c, d, ...]`

and the runtime approximated transmission by alternating pass/stop bands at each cutoff.

That approximation is acceptable for simple single-edge dichroics but **wrong for many spinning-disk multiband dichroics** (for example, CSU-W1-like setups), where real transmission windows are not a strict square-wave alternation between cutoff edges.

## Preferred encoding (authoritative for multiband dichroics)

For `multiband_dichroic` / `polychroic`, describe explicit windows using the existing band object shape:

- `transmission_bands` (preferred when known)
- `reflection_bands` (optional; used directly or as complement source)

Each band object uses:

- `center_nm`
- `width_nm`

Example:

```yaml
component_type: multiband_dichroic
product_code: Di01-T405/488/568/647
transmission_bands:
  - {center_nm: 521, width_nm: 25}
  - {center_nm: 607, width_nm: 25}
reflection_bands:
  - {center_nm: 488, width_nm: 20}
```

## Backward compatibility

The repo keeps compatibility for legacy payloads:

1. **Simple single-edge dichroics** remain valid via `cut_on_nm` or single-value `cutoffs_nm`.
2. **Legacy multiband cutoff-only dichroics** still parse and simulate, but this is treated as a fallback/approximation path.
3. Existing `cutoffs_nm` can remain in instrument files for metadata continuity, but explicit transmission/reflection bands should be treated as authoritative when present.
