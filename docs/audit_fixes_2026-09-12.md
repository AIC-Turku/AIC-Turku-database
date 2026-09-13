# Audit repairs: first correctness batch

This batch addresses confirmed software defects from the 12 September 2026 audit.
It does not certify the instrument ledgers, calibrate the simulator, or resolve
historical hardware configurations.

## Methods generator

- Environmental control, stage/z-stack, autofocus, triggering, and processing
  statements are offered as unchecked acquisition-action choices. Installed
  capabilities no longer become experimental claims automatically.
- A simulator record is a proposal. The user must review the displayed snapshot
  and explicitly confirm its use. Known-invalid records cannot be confirmed;
  conflicting instrument IDs are rejected. Changes to hardware choices revoke
  confirmation. The reviewed record is not re-read from storage at generation.
- The optional acquisition date and session/figure reference distinguish repeated
  acquisitions. The form explicitly states that the date does not reconstruct
  historical hardware or software. Unknown dates may remain blank.
- An unchanged Add click is idempotent. Different selections, dates, or references
  no longer overwrite another acquisition on the same instrument. Clear All
  remains the reset mechanism; per-session editing is a follow-up.
- Compatible optical selections survive route/readout changes. Readouts select
  their parent route; removing that route removes its readouts. Instrument
  changes reset selections, including hidden legacy modalities.
- Missing wavelengths and detector bounds do not become zero. Tuned source
  wavelengths use the actual selected_wavelength_nm field exported by the VM.
- Clipboard success is shown only after a successful write. Failure selects the
  text for manual copying and shows an actionable message.
- Incomplete metadata is labelled as an incomplete draft rather than a blocker
  that misleadingly appears to prohibit generation.

## Virtual microscope

- Bounded detector optimisation uses the detector collection-mask model rather
  than passing a fabricated filter without spectral_ops to the optical model.
- Optimisation requires useful signal for every requested dye, using the same
  intensity/excitation cutoffs as the runtime's existing blocked-path label.
  Zero signal plus zero leakage is not a successful configuration.
- A complete per-dye sequential plan is considered before accepting a shared
  leakage fallback. Partial dye coverage is never advertised as a full plan.
- Disjoint explicit detector-target constraints terminate a splitter path.
  An empty set after propagation is no longer replaced by the preceding path.
- The scoreboard reads excitationStrength and sted.emissionOverlap from the
  actual runtime result contract.
- Invalid/error simulation results are not persisted as importable plans.

## Tests and CI

Install `requirements-test.txt` and run `python -m playwright install chromium`.
Then run `PYTHONPATH=. pytest -q`. The browser regressions execute the production
methods template/script in Chromium with deterministic fetch/storage boundaries;
they are not live-site deployment tests. An additional renderer test checks the
scoreboard against the runtime field names. Public-runtime regressions cover
bounded detectors, dark paths, complete/partial sequential plans, and disjoint
branch targets.

The old lightweight DOM harness now queries attached nodes rather than retaining
removed inputs in selector results. Existing proposal-rendering tests explicitly
confirm their simulator records. CI installs Node and Chromium, runs the complete
suite, and triggers for test/vocabulary/facility/test-dependency changes as well.

## Deliberately deferred

Verified configuration history and effective dates; session editing/export and
full acquisition-setting forms; selection-scoped completeness; canonical-ID
sentence deduplication; broadband-source candidate selection; a full recursive
routing/selector audit; instrument-specific missing optical data; model scope and
readiness UX; payload size reduction; FPbase cancellation/accessibility; and
calibrated physical modelling. No instrument metadata is invented in this batch.
