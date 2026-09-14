# Grounding the AI experiment-planning workflow

The experiment-planning page gives a researcher two things: `llm_inventory.json`
and a prompt. The intended workflow is simple: download the inventory, attach it
to an LLM conversation, describe what you want to do, and use the inventory as
the source for facility-specific facts.

The export should therefore remain useful as an inventory first. The safeguards
below explain what the data establishes and what it does not; they are not a
second recommendation engine.

## What the export establishes

`llm_inventory.json` opens with a `planning_contract` block. It is a statement
about the shape and provenance of the inventory.

| Section | Answers |
| --- | --- |
| `closed_world_fields` | Which route lists are complete enumerations, so absence means "not on this route" rather than "unknown". |
| `availability` | That no booking, access or training data is recorded. |
| `status_semantics` | What an instrument status is derived from, and how to read `status.evidence`. |
| `objective_scope` | That objectives are instrument-level context, not route evidence. |
| `capability_vs_route` | That imaging modes and route types are different authored axes, related by `route_family_coverage`. |

### Open world and closed world

Most of the inventory is open-world: a missing or null value means the fact is
not recorded. Unknown does not mean suitable, unsuitable, available or absent.

Route membership is the important exception. Routes are authored as ordered
`light_paths[]` sequences, so the hardware recorded for a route is a complete
list. A component missing from
`route_hardware_usage[].hardware_inventory_ids` is **not on that route**.

This distinction prevents two opposite hallucinations: inventing hardware on a
route, and treating an unrecorded performance or suitability value as a negative
fact.

### Capability axes and route families

`capabilities.imaging_modes` and `light_paths[].route_type` are different authored
axes. For example, the vocabulary records that some imaging modes are covered by
a broader route family rather than existing as route types themselves.

The authored `vocab/optical_routes.yaml` coverage mapping is exported as
`route_family_coverage`. Each instrument also carries a
`capability_route_reconciliation` derived from that mapping. This lets an LLM
relate an explicitly requested mode such as TIRF or STED to the recorded route
family without inventing a new route type.

`modes_without_a_covering_recorded_route` is the honest "ask staff" signal: it
lists declared modes for which this inventory has no covering recorded route.

### Route-planning summary v2

`llm_context.route_planning_summary` is a convenience view over the authoritative
route contract. Its contract is `route_planning_summary.v2`.

Route-specific optical facts live under `planning_optics`. Installed objectives
are kept separately under `instrument_level_context.installed_objectives` with an
explicit scope note. This separation is deliberate: an objective can be installed
on the microscope without being proven compatible with a particular optical route.

### Instrument status

`evaluate_instrument_status` can return green when no QC or maintenance record
contradicts operation. On a dashboard that is a useful default; in an LLM answer
it can otherwise sound like evidence that a check passed.

Every exported status therefore carries `evidence`:

| Value | Meaning |
| --- | --- |
| `qc_and_maintenance_record` | Both a QC and a maintenance record exist. |
| `qc_record_only` / `maintenance_record_only` | One of the two exists. |
| `no_qc_or_maintenance_record` | Neither exists. The status is the absence of a recorded problem, not a passed check. |

## What the export does not establish

The inventory does not record booking, scheduling, access or training. Terms such
as `available_routes`, `available_positions` and `selected_or_selectable_*` mean
recorded or selectable in the ledger, not free to book.

It also must not be used to invent unrecorded performance or suitability facts.
Examples include frame rate, achievable imaging depth, phototoxicity, long-run
environmental suitability, fluorophore compatibility, sample compatibility,
detector performance, illumination dose and objective-to-route compatibility.
Some of these facts may exist elsewhere in reality; the point is that they are
not established by this inventory unless explicitly recorded here.

Objectives deserve special care. They are recorded at instrument level. Seeing an
objective on an instrument does not prove that the objective is compatible with a
particular optical route.

## The generated prompt

The planning prompt is intentionally conservative. It asks the LLM to identify
recorded candidate instruments/routes and the unknowns that still matter. It does
**not** require a best microscope, a backup, a performance ranking or an
acquisition plan when the inventory cannot support those conclusions.

Users can describe their need in ordinary language. The prompt should not turn a
vague requirement such as "fast", "deep", "low phototoxicity" or "thick cleared
sample" into a facility-specific modality recommendation unless the inventory and
the user's explicit request justify that step.

The generated prompt is also kept under a regression-tested length budget so
additional safeguards do not gradually turn it into an unreadable policy dump.

## Checking a saved answer

`scripts/planning_eval.py` checks an answer offline. It calls no model and no
network:

```bash
PYTHONPATH=. python -m scripts.dashboard_builder
PYTHONPATH=. python -m scripts.planning_eval \
    --inventory dashboard_docs/assets/llm_inventory.json \
    --response saved_answer.md
```

The evaluator derives valid instrument IDs, component IDs and route membership
from the inventory itself. It also derives the instrument-ID prefix shape from the
actual inventory, so ordinary untagged prose such as an invented `scope-...` ID is
checked without hard-coding AIC's prefix convention. Explicit `instrument_id: ...`
tags remain supported, but they are not required for normal saved LLM answers.

It reports:

| Finding | Meaning |
| --- | --- |
| `unknown_instrument_id` | An instrument-ID-shaped claim, tagged or ordinary prose, that the inventory does not record. |
| `unknown_component_id` | A component ID recorded on no active instrument. |
| `component_not_on_named_instrument` | A real component attributed to the wrong instrument. |
| `component_not_on_route` | A component of that instrument attached to a route it is not on. |
| `objective_route_compatibility_unproven` | An installed objective presented as route-compatible when the inventory does not establish that relationship. |
| `exclusive_branch_used_simultaneously` | Two endpoints the records mark mutually exclusive, claimed at once. |
| `availability_claim` | A booking, access or training assertion the inventory cannot ground. |
| `status_claim_without_evidence` | "Operational" repeated for an instrument whose status has no QC or maintenance evidence. |

Exit code is 1 when an error-severity finding is present and 0 otherwise. An
answer that explicitly says availability is unrecorded is not flagged.

The evaluator cannot decide whether microscopy advice is scientifically good. It
only checks grounding against the inventory.

## Scenario suite

`tests/fixtures/planning_scenarios.yaml` contains ten adversarial situations:
long two-colour imaging, fast two-colour dynamics, TIRF, FLIM, deep 3D imaging,
STED, low-phototoxicity time-lapse, a thick cleared sample, a three-colour
route-mixing risk, and an explicit multiphoton request the current inventory
cannot satisfy.

A key rule is that the fixture only encodes a controlled imaging mode or readout
when the user request explicitly names it. Therefore TIRF, STED, FLIM and
multiphoton can be matched against controlled terms. By contrast, "fast",
"deep", "low phototoxicity", "24 h", "cleared sample" and "three-colour" remain
requirements/unknowns rather than being silently translated into spinning disk,
multiphoton, light sheet, widefield or another modality.

The repository-dependent expectations are recomputed from the generated
inventory: explicit controlled-term candidate sets, route-family coverage,
cross-route traps and exclusive branch blocks. The fixtures never encode a
preferred microscope.

## Known residual risks

1. **Size.** The export is large JSON. A chat client may truncate a very large
   attachment, and truncation is itself a grounding risk. Some duplication is
   retained for compatibility with existing consumers.
2. **Prompt instructions are not enforcement.** An LLM can still ignore them.
   `scripts/planning_eval.py` provides a deterministic after-the-fact grounding
   check for explicit identifiers and a few unsupported claim classes.
3. **Raw hardware lists remain instrument-level.** Other consumers use them, so
   they cannot simply be removed. Route membership must still come from the
   authoritative route contract.
4. **The evaluator is not a scientific oracle.** It cannot tell whether a
   recommendation is experimentally sensible; it can only check what the
   repository actually establishes.
