# Canonical light-path v2 architecture

This document defines the repository's canonical light-path model.
It is intended to be the implementation contract for schema cleanup, validator behavior, DTO generation, consumer updates, and future tests.

## 1) Canonical YAML structure

Authoritative instrument light-path data must be encoded using:

```yaml
hardware:
  sources: []
  optical_path_elements: []
  endpoints: []

light_paths:
  - id: <route_id>
    name: <human_readable_name>
    illumination_sequence: []
    detection_sequence: []
```

Canonical top-level light-path fields:

- `hardware.sources`
- `hardware.optical_path_elements`
- `hardware.endpoints`
- `light_paths[]`

Canonical route fields:

- `light_paths[].id`
- `light_paths[].name`
- `light_paths[].illumination_sequence[]`
- `light_paths[].detection_sequence[]`

## 2) Canonical vocabulary and semantics

### `hardware.sources`

Installed illumination sources that can be referenced by route sequences.

- Canonical role in topology: source inventory for `illumination_sequence[]`.
- Source identity must be stable enough to support explicit route references.

### `hardware.optical_path_elements`

Installed optical mechanisms/components that alter or route light before or after the sample plane.

Examples include:

- excitation filter mechanisms
- cube mechanisms
- dichroic mechanisms
- emission filter mechanisms
- selectors
- splitters

Canonical role in topology:

- reusable node inventory referenced by ordered route sequences
- carrier for explicit selector/splitter branch definitions where needed

### `hardware.endpoints`

Explicit route terminals.

Examples include:

- detector endpoints
- camera-port endpoints
- eyepiece endpoints

Canonical role in topology:

- target inventory for `detection_sequence[]`
- explicit branch targets for splitter/selector definitions

### `light_paths`

The ordered route declarations.

Each route must represent one explicit traversable path through the hardware inventory.
`light_paths[]` are the primary source of truth for route topology.

### `illumination_sequence`

Ordered path traversal before the sample plane.

This sequence should contain references to:

- source entries
- optical path element entries

Its purpose is to define the real illumination ordering, not just membership.

### `detection_sequence`

Ordered path traversal after the sample plane.

This sequence should contain references to:

- optical path element entries
- endpoint entries

Its purpose is to define the real detection ordering, not just membership.

### `modalities`

`modalities` on `hardware.sources`, `hardware.optical_path_elements`, or `hardware.endpoints` are validation aids only.

They may be used to:

- sanity-check route membership
- detect invalid route assignments
- support validation/reporting summaries

They must **not** be treated as the primary topology definition.
If sequence ordering and modality hints disagree, the ordered route declarations are the authoritative topology and the disagreement should be surfaced by validation.

### `branches` / selectors / splitters

Branching must remain explicitly representable in canonical YAML.

Canonical requirements:

- selector/splitter semantics must survive `YAML -> schema/validator -> DTO -> consumers`
- branch identity must be stable
- branch endpoints must be explicit
- branch-specific optics must remain possible where already supported or where the schema can represent them cleanly

Implications:

- selector/splitter behavior belongs on the relevant `hardware.optical_path_elements[]` entry
- branches must carry stable IDs
- branches should reference explicit endpoint IDs rather than relying on inferred terminals
- where a branch contains its own optical component payload, that payload must remain preserved through normalization and DTO export

## 3) Data flow contract

The expected repository flow is:

`YAML -> schema/validator -> DTO -> consumers`

### YAML

Instrument YAML is the authoritative authored record.
It declares the installed source inventory, optical path elements, endpoints, and the ordered route sequences.

### Schema / validator

`schema/instrument_policy.yaml` and `scripts/validate.py` together define and enforce the canonical authoring contract.

Responsibilities:

- define canonical field names
- validate structural correctness
- validate controlled vocabulary use
- validate explicit route references
- report migration/deprecation usage where legacy fields still appear

### DTO

The DTO is the consumer contract generated from canonical YAML.

Authoritative normalized DTO shape:

```yaml
dto_schema: light_paths_v2
metadata:
  authoritative_contract: canonical_v2_only
  topology_truth: light_paths
  wavelength_grid: {...}
simulation:
  default_route: <route_id>
  route_catalog: []
  graph_incomplete: <bool>
sources: []
optical_path_elements: []
endpoints: []
light_paths: []
projections:
  virtual_microscope:
    # Derived runtime/UI adapter only; not authoritative topology.
    light_sources: []
    detectors: []
    terminals: []
    stages: {}
    splitters: []
    valid_paths: []
```

Responsibilities:

- preserve canonical route ordering
- preserve explicit endpoints
- preserve selector/splitter semantics
- preserve stable branch IDs and branch targets
- preserve branch-specific optics where modeled
- keep `sources`, `optical_path_elements`, `endpoints`, and `light_paths` as the only authoritative topology contract
- keep runtime/UI convenience structures under explicit derived adapters such as `projections.virtual_microscope`

Consumers must use the DTO contract rather than reconstructing topology ad hoc from raw YAML.

### Consumers

Current consumer layers include:

- dashboard build/export logic
- instrument spec pages
- methods generator export/UI
- virtual microscope payload/runtime/app
- audit tooling

These layers should treat the DTO as authoritative consumer input.

## 4) What is no longer canonical

The following structures are migration-only compatibility layers and must not be treated as canonical authoring targets:

- legacy `hardware.light_path.*` mechanism trees
- deprecated flat filter/splitter structures
- alias-only field spellings retained solely for compatibility

Compatibility behavior may remain temporarily in migration helpers, validators, or parser normalization code, but:

- new authoring should target the canonical v2 model
- new tests should primarily assert canonical v2 behavior
- cleanup work should remove assumptions that legacy topology is a co-equal source of truth

## 5) Implementation consequences

This documentation implies the following repository rules:

1. The schema must describe the canonical v2 structure unambiguously.
2. Generated templates must be derived from that canonical schema and must not drift from it.
3. Validation must treat ordered sequences as authoritative.
4. DTO generation must preserve explicit routing and branch semantics without inventing hidden topology.
5. Consumer code must rely on the DTO contract instead of raw-YAML inference.

## 6) Migration note

Legacy structures may still be normalized during cutover so existing records can be migrated safely.
That migration path is transitional only.

Remaining compatibility layers are intentionally narrow:

- the explicit legacy import/migration helpers in `scripts/light_path_parser.py`
- validator/schema coverage that still recognizes legacy paths for migration-only audits
- derived runtime splitter compatibility fields such as `path1` / `path2`, kept only so
  approximation-mode projections can consume old payloads without teaching them as canonical

None of the above compatibility paths should be used as new authoring targets.

The end state is:

- canonical YAML authoring in v2 structure
- schema/validator aligned to v2
- DTO aligned to v2
- consumers aligned to DTO
- tests written against the canonical model
