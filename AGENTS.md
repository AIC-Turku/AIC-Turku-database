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

## Testing Guidance

- Run targeted pytest tests for parser, validator, dashboard builder, LLM export, methods page export, and VM contract.
- Run JS syntax checks:
  - `node --check scripts/templates/virtual_microscope_runtime.js`
  - `node --check scripts/templates/virtual_microscope_app.js`
- If full pytest is slow, run the narrowest relevant tests and report what was run.

## Change Scope Guardrail

Do not change runtime behavior in this step except adding AGENTS.md.
