"""Selected-execution projection for light-path routes.

This module owns the runtime-selected execution model derived from static
route topology.

It converts route_steps into selected_route_steps and explicitly distinguishes:
- fixed steps
- authored resolved optical-component steps
- unresolved multi-position optical-component steps requiring runtime selection

It should not parse canonical YAML, import legacy topology, validate contracts,
build route graphs, or generate VM payloads.
"""

from __future__ import annotations

from typing import Any

from scripts.lightpath.model import (
    CUBE_LINK_KEYS,
    _clean_identifier,
    _clean_string,
    _coerce_number,
)
from scripts.lightpath.route_graph import (
    _iter_element_positions,
    _resolve_position_candidate_payload,
)


def _build_selected_route_steps(
    route_steps: list[dict[str, Any]],
    route_id: str,
    element_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build the runtime-selected execution model from static route topology.

    Unlike ``route_steps`` — which may still be used as a topology projection —
    this structure explicitly distinguishes:
    - fixed steps
    - authored resolved steps
    - unresolved multi-position steps that require a runtime selection

    The unresolved state carries parser-authoritative ``available_positions`` so
    the browser does not need to infer optics or invent position identity.
    """
    selected: list[dict[str, Any]] = []

    def _available_positions_for_element(
        element: dict[str, Any],
    ) -> list[dict[str, Any]]:
        candidates = _iter_element_positions(element)
        out: list[dict[str, Any]] = []

        for key_text, slot, position in candidates:
            if not isinstance(position, dict):
                continue

            (
                component,
                authored_position_id,
                position_key,
                position_label,
            ) = _resolve_position_candidate_payload(
                position,
                parent_element=element,
                fallback_key=key_text,
                fallback_slot=slot,
            )

            if not component:
                continue

            entry: dict[str, Any] = {
                "position_id": authored_position_id,
                "selected_position_id": authored_position_id,
                "position_key": position_key,
                "selected_position_key": position_key,
                "position_label": position_label,
                "selected_position_label": position_label,
                "slot": slot,
                "label": position_label,
                "component_type": (
                    _clean_string(component.get("component_type")).lower()
                    or None
                ),
                "selection_mode": (
                    _clean_string(element.get("selection_mode")).lower()
                    or "exclusive"
                ),
                "spectral_ops": component.get("spectral_ops"),
            }

            compatible_source_ids = position.get("compatible_source_ids")
            if isinstance(compatible_source_ids, list):
                normalized_source_ids = [
                    _clean_identifier(source_id)
                    for source_id in compatible_source_ids
                    if _clean_identifier(source_id)
                ]
                if normalized_source_ids:
                    entry["compatible_source_ids"] = normalized_source_ids

            # Identity is authored on the position itself. The resolved component
            # payload is only a fallback, and its ``name`` defaults to the parent
            # element's name (see ``_component_payload``), so a position that
            # records no name of its own would otherwise inherit the holder's name
            # and be published as "the Filter Turret in the Filter Turret".
            parent_name = _clean_string(element.get("name"))
            for identity_field in (
                "manufacturer",
                "model",
                "product_code",
                "name",
            ):
                val = (
                    _clean_string(position.get(identity_field))
                    or _clean_string(component.get(identity_field))
                )
                if not val:
                    continue
                if identity_field == "name" and val == parent_name:
                    continue
                entry[identity_field] = val

            if component.get("_unsupported_spectral_model"):
                entry["_unsupported_spectral_model"] = True

            if component.get("_cube_incomplete"):
                entry["_cube_incomplete"] = True

            comp_type = _clean_string(component.get("component_type")).lower()
            if comp_type == "filter_cube":
                for cube_key in CUBE_LINK_KEYS:
                    sub = component.get(cube_key)
                    if isinstance(sub, dict):
                        entry[cube_key] = sub

            out.append(entry)

        return out

    def _element_requires_position_selection(
        element: dict[str, Any],
    ) -> bool:
        """Return True when a mechanism cannot safely be treated as fixed.

        A selector with one *recorded* position is not necessarily fixed.  If the
        hardware declares more physical slots than are documented, the omitted
        slots are unknown rather than evidence that the sole recorded position was
        always selected.  This matters for partially documented camera filter
        wheels such as the CSU-W1 Evolve branch.
        """
        positions = _iter_element_positions(element)
        if len(positions) > 1:
            return True

        slot_count = _coerce_number(element.get("slots"))
        return bool(
            len(positions) == 1
            and slot_count is not None
            and slot_count > 1
        )

    def _derive_selection_state(
        step: dict[str, Any],
    ) -> tuple[str, list[dict[str, Any]] | None]:
        kind = step.get("kind", "")

        if kind in {"source", "detector", "endpoint", "sample", "routing_component"}:
            return "fixed", None

        authored = step.get("_authored_position_id")
        if authored:
            # Only mark as resolved when the position was actually found.
            # If the authored position_id did not match any position,
            # walk_sequence leaves "position_id" absent while still recording
            # "_authored_position_id".  In that case the authored position was
            # invalid: expose it as unresolved so the browser can surface the
            # issue and show available positions rather than silently resolving
            # to a wrong component.
            if step.get("position_id"):
                return "resolved", None
            # Authored but invalid/unresolved — expose available positions.
            element_id = _clean_identifier(step.get("component_id"))
            element_row = element_lookup.get(element_id, {})
            return "unresolved", _available_positions_for_element(element_row)

        element_id = _clean_identifier(step.get("component_id"))
        element_row = element_lookup.get(element_id, {})
        positions = _iter_element_positions(element_row)

        if not _element_requires_position_selection(element_row):
            return "fixed", None

        return "unresolved", _available_positions_for_element(element_row)

    def _process_branch_sequence(
        seq: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        resolved_seq: list[dict[str, Any]] = []

        for branch_step in seq:
            if not isinstance(branch_step, dict):
                continue

            kind = branch_step.get("kind", "")
            available: list[dict[str, Any]] | None = None

            if kind in {"source", "detector", "endpoint"}:
                selection_state = "fixed"
            else:
                authored = branch_step.get("_authored_position_id")
                elem_id = _clean_identifier(branch_step.get("component_id"))
                elem_row = element_lookup.get(elem_id, {})
                if authored and branch_step.get("position_id"):
                    selection_state = "resolved"
                elif authored:
                    # Match top-level behavior: an authored but unknown branch-local
                    # position must not silently resolve to the first recorded slot.
                    selection_state = "unresolved"
                    available = _available_positions_for_element(elem_row)
                elif _element_requires_position_selection(elem_row):
                    selection_state = "unresolved"
                    available = _available_positions_for_element(elem_row)
                else:
                    selection_state = "fixed"

            entry: dict[str, Any] = {
                "kind": branch_step.get("kind"),
                "component_id": branch_step.get("component_id"),
                "display_label": branch_step.get("display_label"),
                # Kept so the dashboard can index a branch-local element (e.g. a
                # per-camera filter wheel) by inventory id the same way it
                # indexes a top-level step, and offer its recorded positions.
                "hardware_inventory_id": branch_step.get("hardware_inventory_id"),
                "stage_role": branch_step.get("stage_role"),
                "selection_state": selection_state,
                "unsupported_reason": branch_step.get("unsupported_reason"),
            }

            if selection_state == "unresolved":
                entry["selected_position_id"] = None
                entry["selected_position_key"] = None
                entry["selected_position_label"] = None
                entry["position_id"] = None
                entry["position_key"] = None
                entry["position_label"] = None
                entry["spectral_ops"] = None
                entry["available_positions"] = available
            else:
                entry["selected_position_id"] = branch_step.get("position_id")
                entry["selected_position_key"] = branch_step.get("position_key")
                entry["selected_position_label"] = branch_step.get("position_label")
                entry["position_id"] = branch_step.get("position_id")
                entry["position_key"] = branch_step.get("position_key")
                entry["position_label"] = branch_step.get("position_label")
                entry["spectral_ops"] = branch_step.get("spectral_ops")

            if kind == "source":
                entry["source_id"] = branch_step.get("source_id")
            elif kind == "detector":
                entry["detector_id"] = branch_step.get("detector_id")
                entry["endpoint_id"] = branch_step.get("endpoint_id")
            elif kind == "endpoint":
                entry["endpoint_id"] = branch_step.get("endpoint_id")

            resolved_seq.append(entry)

        return resolved_seq

    for step in route_steps:
        if not isinstance(step, dict):
            continue

        selection_state, available = _derive_selection_state(step)

        entry: dict[str, Any] = {
            "route_step_id": step.get("step_id"),
            "step_id": step.get("step_id"),
            "route_id": route_id,
            "order": step.get("order"),
            "phase": step.get("phase"),
            "kind": step.get("kind"),
            "mechanism_id": (
                step.get("component_id")
                if step.get("kind") == "optical_component"
                else None
            ),
            "element_id": (
                step.get("component_id")
                if step.get("kind") == "optical_component"
                else None
            ),
            "component_id": step.get("component_id"),
            "source_id": step.get("source_id"),
            "detector_id": step.get("detector_id"),
            "endpoint_id": step.get("endpoint_id"),
            "hardware_inventory_id": step.get("hardware_inventory_id"),
            "selection_state": selection_state,
            "display_label": step.get("display_label"),
            "component_type": (
                step.get("component_type")
                if selection_state != "unresolved"
                else None
            ),
            "stage_role": step.get("stage_role"),
            "metadata": step.get("metadata", {}),
            "unsupported_reason": step.get("unsupported_reason"),
        }

        if selection_state == "unresolved":
            entry["selected_position_id"] = None
            entry["selected_position_key"] = None
            entry["selected_position_label"] = None
            entry["position_id"] = None
            entry["position_key"] = None
            entry["position_label"] = None
            entry["spectral_ops"] = None
            entry["available_positions"] = available
        else:
            entry["selected_position_id"] = step.get("position_id")
            entry["selected_position_key"] = step.get("position_key")
            entry["selected_position_label"] = step.get("position_label")
            entry["position_id"] = step.get("position_id")
            entry["position_key"] = step.get("position_key")
            entry["position_label"] = step.get("position_label")
            entry["spectral_ops"] = step.get("spectral_ops")

        if step.get("kind") == "routing_component" and isinstance(
            step.get("routing"),
            dict,
        ):
            entry["routing"] = {
                "selection_mode": step["routing"].get("selection_mode"),
                "branches": [
                    {
                        "branch_id": br.get("branch_id"),
                        "label": br.get("label"),
                        "mode": br.get("mode"),
                        "sequence": _process_branch_sequence(
                            br.get("sequence") or []
                        ),
                    }
                    for br in step["routing"].get("branches", [])
                    if isinstance(br, dict)
                ],
            }
        elif step.get("routing") is not None:
            entry["routing"] = step.get("routing")
        else:
            entry["routing"] = None

        selected.append(entry)

    return selected


__all__ = [
    "_build_selected_route_steps",
]
