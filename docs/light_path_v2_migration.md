# Canonical light-path v2 architecture

This document defines the repository's canonical light-path model.
It is the implementation contract for schema, validator behavior, DTO generation, consumers, and tests.

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
- inventory/capability metadata only for selectors/splitters
- may advertise supported branch modes/counts, but not canonical downstream routing truth

### `hardware.endpoints`

Explicit route terminals.

Examples include:

- detector endpoints
- camera-port endpoints
- eyepiece endpoints

Canonical role in topology:

- target inventory for `detection_sequence[]`
- explicit route terminals referenced directly from branch-local sequences
- normalized together with endpoint-capable inventories (for example `hardware.detectors[]` and `hardware.eyepieces[]`) before DTO/runtime consumption

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

Branching remains explicitly representable in canonical YAML, but the route fork now belongs to `light_paths`, not to `hardware`.

Canonical v1 branch model:

- only `light_paths[].detection_sequence[]` items can carry a tagged `branches` block
- each branch block declares `selection_mode`
- each branch block declares `items[]`
- each branch item declares `branch_id`, optional `label`, and a linear `sequence[]`
- branch-local sequences may include additional `optical_path_element_id` entries before the final `endpoint_id`
- branch-local sequences are strict tagged unions and must terminate at explicit `endpoint_id` values when the downstream endpoint is known
- nested branch blocks inside branch-local sequences are intentionally out of scope in v1

Validation behavior:

- route and branch-local endpoint termination is checked, and ambiguous termination is surfaced as a warning
- deprecated hardware-owned routing such as `hardware.optical_path_elements[].branches[].target_ids` must not be treated as canonical topology

Example:

```yaml
light_paths:
  - id: epi
    detection_sequence:
      - optical_path_element_id: trinocular_port_selector
      - branches:
          selection_mode: exclusive
          items:
            - branch_id: camera_route
              label: To Camera
              sequence:
                - optical_path_element_id: optovar_1p5x
                - endpoint_id: detector_1
            - branch_id: eyepiece_route
              label: To Eyepieces
              sequence:
                - endpoint_id: eyepieces
```

Hardware splitters/selectors still exist as inventory entries under `hardware.optical_path_elements[]`, but their canonical role is limited to:

- identifying the installed selector/splitter element
- advertising capability metadata such as `selection_mode`, `supported_branch_modes`, and `supported_branch_count`
- providing optional optical/component metadata for the installed part itself

Canonical downstream routing truth must no longer be authored as `hardware.optical_path_elements[].branches[].target_ids`.

## 3) Data flow contract

The expected repository flow is:

`YAML -> schema/validator -> DTO -> consumers`

### YAML

Instrument YAML is the authoritative authored record.
It declares the installed source inventory, optical path elements, endpoints, and the ordered route sequences.

### Schema / validator

`schema/instrument_policy.yaml` and `scripts/validation/*` (via the `scripts/validate.py`
compatibility façade) define and enforce the canonical authoring contract.

Responsibilities:

- define canonical field names
- validate structural correctness
- validate controlled vocabulary use
- validate explicit route references
- report legacy or deprecated field usage where present

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
- preserve route-owned branch blocks, stable branch IDs, and branch-local sequences
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

## 4) What is not canonical

The following structures are legacy compatibility layers and must not be treated as canonical authoring targets:

- legacy `hardware.light_path.*` mechanism trees
- deprecated flat filter/splitter structures
- alias-only field spellings retained solely for compatibility

Compatibility behavior is limited to legacy import helpers and validator audit paths:

- new authoring must target the canonical v2 model
- new tests must primarily assert canonical v2 behavior
- canonical `light_paths[]` sequences are the authoritative topology truth

## 5) Implementation consequences

This documentation implies the following repository rules:

1. The schema must describe the canonical v2 structure unambiguously.
2. Generated templates must be derived from that canonical schema and must not drift from it.
3. Validation must treat ordered sequences as authoritative.
4. DTO generation must preserve explicit routing and branch semantics without inventing hidden topology.
5. Consumer code must rely on the DTO contract instead of raw-YAML inference.

## 6) Retained compatibility layers

Remaining compatibility layers are intentionally narrow and must not be used as new authoring targets:

- `scripts/lightpath/legacy_import.py` — explicit legacy import adapter (migration/audit tooling only).
- `scripts/validate.py` — compatibility façade; implementations in `scripts/validation/*`.
- Validator schema coverage that still recognizes legacy paths for audit-only diagnostics.
- Derived runtime splitter compatibility fields such as `path1` / `path2`, kept only so
  approximation-mode projections can consume older payloads without treating them as canonical.

Current production state:

- canonical YAML authoring is in v2 structure
- schema/validator is aligned to v2
- DTO is aligned to v2
- consumers use the DTO contract
