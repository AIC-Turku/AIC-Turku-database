# AIC-Turku Database Dataflow Rules

## Authoritative Dataflow

All production data should flow through this single authoritative path:

YAML instrument specs
-> schema validation
-> canonical parser / normalizer DTOs
-> derived view DTOs
-> dashboard display
-> LLM inventory export
-> methods page
-> virtual microscope
-> audit/reporting tools

## Required Rules

1. YAML is the authored source of truth.
2. Schema and validation define what valid YAML means.
3. Canonical DTOs are the source of truth for downstream code.
4. Dashboard pages, LLM inventory files, methods pages, and the virtual microscope must all consume canonical DTOs or explicitly named derived view DTOs generated from canonical DTOs.
5. Downstream code must not independently reinterpret raw YAML when canonical DTO data is available.
6. Downstream code must not invent missing hardware, optical-path, method, route, source, detector, software, or metadata values.
7. Missing required DTO fields should produce explicit diagnostics, not silent fallbacks.
8. Derived display DTOs are allowed, but they must be clearly separated from canonical DTOs.
9. The virtual microscope must use the canonical light-path DTO, not dashboard display DTOs.
10. The dashboard display may use dashboard-specific view DTOs, but those view DTOs must be derived from canonical DTOs.
11. The LLM inventory export must use canonical DTOs plus explicitly documented derived summaries.
12. The methods page must use canonical instrument/method DTOs plus explicitly documented derived summaries.
13. Legacy import/adapters are allowed only in migration or audit tooling, not in production build paths unless explicitly marked as compatibility mode.
14. Route IDs, route names, route order, splitter branch IDs, selected execution, method metadata, display names, instrument status, and hardware capabilities must come from YAML/schema/canonical DTOs.
15. Avoid hardcoded vocabularies, hidden aliases, compatibility fallbacks, and UI-side inference in production dataflow.
16. If a display needs a fallback label such as "Unknown", it must be visibly diagnostic and must not be used as authoritative data.

## Ledger Updates

`docs/ledger_gaps.md` lists what the instrument records do not yet say — the light
sources with no recorded role, the detectors no light path reaches, the filter
positions with no transmission bands, and so on. It is what the public tools
cannot work around, so it is the working list of questions for facility staff.

It is generated from the records, not maintained by hand:

- after changing any file under `instruments/` (including `instruments/retired/`),
  run `python -m scripts.ledger_gaps` and commit the regenerated
  `docs/ledger_gaps.md` in the same change;
- `python -m scripts.ledger_gaps --check` exits non-zero when the committed file no
  longer matches the records. Run it before proposing a ledger change, and treat a
  failure as "regenerate", never as "edit the Markdown".

Filling a gap should make the list shorter. If a ledger edit leaves the count
unchanged, the field that was edited is not one the tools depend on, which is worth
saying explicitly in the change description. Where a field is genuinely not
applicable to an instrument, record that explicitly rather than leaving it blank:
the tools can then stop asking, and the entry leaves this list.

Never fill a gap by assumption to make the list shorter. An unrecorded fact is a
question for staff, not a value to invent.

## Testing Guidance

- Run targeted pytest tests for parser, validator, dashboard builder, LLM export, methods page export, and VM contract.
- Run JS syntax checks:
  - `node --check scripts/templates/virtual_microscope_runtime.js`
  - `node --check scripts/templates/virtual_microscope_app.js`
- If full pytest is slow, run the narrowest relevant tests and report what was run.

## Change Scope Guardrail

Do not change runtime behavior in this step except adding AGENTS.md.

## Microscope inventory reviews

- Read complete instrument YAML files, including retired records, not just generated pages or audit totals. Keep synthetic fixtures separate from staff questions.
- Trace each declared route from its sources, through optics and branches, to the actual detector or eyepiece. Look for unreferenced hardware and conflicts between installed capabilities and route definitions. Do not assume every microscope has an epi-fluorescence layout.
- Distinguish missing hardware facts from not-applicable metadata, unsupported models, historical uncertainty and experiment-specific settings. A broadband lamp does not need an invented single wavelength.
- Correct only facts supported by existing records or primary documentation for the exact recorded component. Link evidence in the ledger or review document. Unknown optics are not empty positions; nominal specifications are not measured transmission curves.
- For unresolved facts, draft short microscope-specific Slack questions in plain language: the software name/version, component label, data sheet, room, or a simple light-path drawing. Do not repeat information already present or ask staff to dismantle instruments.
- Ask when hardware/software changes took effect and how that date is known. Do not use Git commit dates as installation dates.
- Keep staff questions separate from implementation defects. Never invent data to make a completeness check pass. Submit fixes in a PR; do not merge or post Slack messages without explicit authorization.
