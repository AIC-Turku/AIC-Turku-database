# Grounding the AI experiment-planning workflow

The experiment-planning page gives a researcher two things: `llm_inventory.json`
and a prompt. They paste both into an assistant of their choosing. Nothing in
this repository sees the answer, so the export and the prompt are the only points
where a hallucinated recommendation can be prevented.

This page records what the export establishes, what it deliberately does not, and
how to check an answer after the fact.

## What the export establishes

`llm_inventory.json` opens with a `planning_contract` block. It is not advice; it
is a statement about the shape and provenance of the data that follows.

| Section | Answers |
| --- | --- |
| `closed_world_fields` | Which lists are complete enumerations, so absence means "not on this route" rather than "unknown". |
| `availability` | That no booking, access or training data is recorded at all. |
| `status_semantics` | What an instrument status is derived from, and how to read `status.evidence`. |
| `objective_scope` | That objectives are recorded per instrument, not per route. |
| `capability_vs_route` | That imaging modes and route types are different authored axes, related by `route_family_coverage`. |

### Open world and closed world

Most of the export is open-world: a missing or null value means the fact is not
recorded, and unknown never means "fine" or "absent". This is stated in
`policy.do_not_infer_constraints` and is the right default for hardware metadata.

Route membership is the exception. Routes are authored as ordered
`light_paths[]` sequences, so the hardware a route uses is a complete list. A
component missing from `route_hardware_usage[].hardware_inventory_ids` is **not
on that route**.

Both rules are needed, and they contradict each other unless the boundary is
stated. Without it, the only way left to decide whether a laser can be used on a
route is to guess — which is exactly the failure this export exists to prevent.

### Capability axes and route families

`vocab/optical_routes.yaml` records six route families. There is no `tirf`,
`sted`, `sim` or `smlm` route type: those acquisitions are recorded as
`widefield_fluorescence` or `confocal_point` routes, and the vocabulary's
`covers.imaging_modes` mapping says so.

That mapping is exported as `route_family_coverage`, and each instrument carries
a `capability_route_reconciliation` derived from it. Without them, an instrument
declaring `tirf` while every recorded route is `widefield_fluorescence` looks
like a contradiction, and a planner has to pick a wrong answer: invent a TIRF
route, or report that the facility has no TIRF.

`modes_without_a_covering_recorded_route` is the honest "ask staff" signal: it
lists declared modes with no recorded route in this export.

### Instrument status

`evaluate_instrument_status` returns green when nothing contradicts it, so an
instrument with no recorded history reports the same "🟢 Online / Operational" as
one that passed QC last week. On a dashboard that is a reasonable default. Passed
to a researcher by an assistant, it becomes a claim that a check was performed.

Every exported status therefore carries `evidence`:

| Value | Meaning |
| --- | --- |
| `qc_and_maintenance_record` | Both a QC and a maintenance record exist. |
| `qc_record_only` / `maintenance_record_only` | One of the two exists. |
| `no_qc_or_maintenance_record` | Neither exists. The status is the absence of a recorded problem, not a passed check. |

## What the export does not record

- Booking, scheduling, access or training. `available_routes`,
  `available_positions` and `selected_or_selectable_*` mean recorded or
  selectable in the ledger, never free to book.
- Measured system throughput, detector QE curves, frame rates, imaging depth
  limits, illumination dose or phototoxicity thresholds.
- Whether a given objective is usable on a given route.
- Whether two endpoints in an exclusive branch block can be used at once. The
  records say they cannot; the ledger does not describe alternatives.

The prompt tells the assistant to report these as unknown and to send the user to
facility staff. It does not ask the assistant to rank instruments on any of them.

## Checking a saved answer

`scripts/planning_eval.py` checks an answer offline. It calls no model and no
network, so it runs in CI without an API key:

```bash
PYTHONPATH=. python -m scripts.dashboard_builder          # generates the inventory
PYTHONPATH=. python -m scripts.planning_eval \
    --inventory dashboard_docs/assets/llm_inventory.json \
    --response saved_answer.md
```

It reports:

| Finding | Meaning |
| --- | --- |
| `unknown_instrument_id` | An instrument the facility does not record. |
| `unknown_component_id` | A component recorded on no active instrument. |
| `component_not_on_named_instrument` | A real component attributed to the wrong instrument. |
| `component_not_on_route` | A component of that instrument attached to a route it is not on. |
| `exclusive_branch_used_simultaneously` | Two endpoints the records mark mutually exclusive, claimed at once. |
| `availability_claim` | A booking, access or training claim the inventory cannot ground. |
| `status_claim_without_evidence` | "Operational" repeated for an instrument with no QC or maintenance record. |

Exit code is 1 when any error-severity finding is present, 0 otherwise.

An answer that *states* availability is unrecorded is not flagged — that is the
behaviour the prompt asks for. The harness only flags assertions.

What it cannot check is whether the microscopy advice is good. It answers one
question: is every identifier in this answer traceable to the inventory.

## Scenario suite

`tests/fixtures/planning_scenarios.yaml` holds ten planning situations — live
two-colour imaging, fast dynamics, TIRF, FLIM, deep 3D, STED, low-phototoxicity
time-lapse, a cleared sample, a three-colour route conflict, and a request the
recorded inventory cannot satisfy.

Each scenario records expectations *about the ledger*, never a preferred
microscope: which instruments declare the required terms, which route families
cover them, which components are recorded on the instrument but not on a given
route, which branch blocks are exclusive, and what must remain unknown.

`tests/test_planning_grounding.py` recomputes every one of those expectations
from the generated inventory. If the ledger changes, the fixture fails and names
the drift instead of silently preserving a stale answer.

## Known residual risks

1. **Size.** The export is about 1.9 MB of JSON. A chat client may truncate it,
   and a truncated inventory is a hallucination source no contract can fix. Some
   of that is duplication: `route_planning_summary` appears both under
   `llm_context.derived_summaries` and at `llm_context.route_planning_summary`,
   and `hardware_focus_summary` is likewise duplicated. Removing either is a
   breaking change for existing consumers and has not been attempted here.
2. **Prose mitigations are not enforcement.** The contract, the policy notes and
   the prompt all describe correct behaviour. Nothing makes an assistant follow
   them; `scripts/planning_eval.py` is the only check, and it runs after the
   fact on an answer someone chooses to save.
3. **Raw hardware lists remain first in each record.** `hardware.sources`,
   `hardware.detectors` and `hardware.objectives` carry no route binding. They
   are retained because other consumers read them, and the route-bound view is
   reachable from `llm_context`. A model that reads only the top of a record
   still sees an unbound bag of components.
4. **The harness is identifier-level.** It cannot tell whether a recommendation
   is scientifically sensible, only whether it names things that exist and
   attaches them to routes that record them.
