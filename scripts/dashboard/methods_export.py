"""Methods-generator dashboard export.

This module owns the methods-generator derived export projection.

Authoritative production dataflow:

    YAML
    -> strict validation
    -> canonical build context / canonical DTOs
    -> derived exports:
       dashboard_view
       llm_inventory
       methods_export
       vm_payload

This module must not import scripts.dashboard_builder.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

from scripts.build_context import clean_text


def _build_ack_data(ack: dict[str, Any]) -> dict[str, Any]:
    """Normalize acknowledgement copy for frontend configuration."""
    return {
        "standard": str(ack.get("standard", "")),
        "xcelligence_addition": str(ack.get("xcelligence_addition", "")),
    }


def build_methods_generator_page_config(
    facility: dict[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    """Build frontend config for the methods generator page."""
    ack_override_path = repo_root / "acknowledgements.yaml"

    if ack_override_path.is_file():
        with ack_override_path.open(encoding="utf-8") as handle:
            override_ack = yaml.safe_load(handle.read()) or {}

        if not isinstance(override_ack, dict):
            override_ack = {}

        ack_data = _build_ack_data(override_ack)
    else:
        facility_ack = (
            facility.get("acknowledgements", {})
            if isinstance(facility.get("acknowledgements"), dict)
            else {}
        )
        ack_data = _build_ack_data(facility_ack)

    methods_config = (
        facility.get("methods_generator", {})
        if isinstance(facility.get("methods_generator"), dict)
        else {}
    )

    return {
        "output_title": str(
            methods_config.get("output_title", "Light Microscopy Methods")
        ),
        "instrument_data_url": str(
            methods_config.get(
                "instrument_data_url",
                "../assets/instruments_data.json",
            )
        ),
        "acknowledgements": ack_data,
    }


def build_plan_experiments_page_config(facility: dict[str, Any]) -> dict[str, Any]:
    """Build frontend config for the experiment-planning page."""
    planner_config = (
        facility.get("plan_experiments", {})
        if isinstance(facility.get("plan_experiments"), dict)
        else {}
    )

    facility_short_name = str(
        facility.get("short_name")
        or facility.get("full_name")
        or "Core Imaging Facility"
    )
    facility_contact_url = str(facility.get("contact_url", "#"))

    return {
        "facility_short_name": facility_short_name,
        "facility_contact_url": facility_contact_url,
        "facility_contact_label": str(
            planner_config.get(
                "contact_button_label",
                f"Contact {facility_short_name} Staff",
            )
        ),
        "llm_inventory_asset_url": str(
            planner_config.get(
                "llm_inventory_asset_url",
                "assets/llm_inventory.json",
            )
        ),
    }


def build_methods_generator_instrument_export(inst: dict[str, Any]) -> dict[str, Any]:
    """Build methods export DTO from canonical instrument + canonical light-path DTOs.

    Methods export must not infer undocumented capabilities. Missing canonical fields
    are surfaced as diagnostics instead of invented fallback text.
    """
    canonical = copy.deepcopy(
        inst.get("canonical_instrument_dto")
        or inst.get("canonical")
        or {}
    )
    lightpath = copy.deepcopy(
        inst.get("canonical_lightpath_dto")
        or inst.get("lightpath_dto")
        or {}
    )

    canonical_instrument = (
        canonical.get("instrument")
        if isinstance(canonical.get("instrument"), dict)
        else {}
    )

    dto: dict[str, Any] = {
        "id": clean_text(
            inst.get("id")
            or canonical_instrument.get("instrument_id")
        ),
        "display_name": clean_text(
            inst.get("display_name")
            or canonical_instrument.get("display_name")
        ),
    }

    diagnostics: list[dict[str, str]] = []

    canonical_hardware = (
        canonical.get("hardware")
        if isinstance(canonical.get("hardware"), dict)
        else {}
    )
    canonical_software = (
        canonical.get("software")
        if isinstance(canonical.get("software"), list)
        else []
    )

    if not canonical_hardware:
        diagnostics.append(
            {
                "severity": "warning",
                "code": "missing_canonical_hardware",
                "path": "canonical.hardware",
                "message": "missing in DTO: canonical.hardware",
                "source": "methods_export",
                "affected_export": "methods",
            }
        )

    if not canonical_software:
        diagnostics.append(
            {
                "severity": "warning",
                "code": "missing_canonical_software",
                "path": "canonical.software",
                "message": "missing in DTO: canonical.software",
                "source": "methods_export",
                "affected_export": "methods",
            }
        )

    canonical_routes = [
        {
            "id": clean_text(route.get("id")),
            "display_label": clean_text(
                route.get("name")
                or route.get("display_label")
                or route.get("id")
            ),
            "route_order": index,
        }
        for index, route in enumerate(lightpath.get("light_paths") or [])
        if isinstance(route, dict) and clean_text(route.get("id"))
    ]

    if not canonical_routes:
        diagnostics.append(
            {
                "severity": "warning",
                "code": "missing_canonical_routes",
                "path": "lightpath_dto.light_paths",
                "message": "missing in DTO: lightpath_dto.light_paths",
                "source": "methods_export",
                "affected_export": "methods",
            }
        )

    if any(
        not isinstance(route.get("selected_execution"), dict)
        for route in (lightpath.get("light_paths") or [])
        if isinstance(route, dict)
    ):
        diagnostics.append(
            {
                "severity": "error",
                "code": "missing_selected_execution",
                "path": "lightpath_dto.light_paths[].selected_execution",
                "message": "missing in DTO: selected_execution.selected_route_steps",
                "source": "methods_export",
                "affected_export": "methods",
            }
        )

    methods_view_dto = {
        "objectives": copy.deepcopy(canonical_hardware.get("objectives") or []),
        "detectors": copy.deepcopy(canonical_hardware.get("detectors") or []),
        "light_sources": copy.deepcopy(
            canonical_hardware.get("sources")
            or canonical_hardware.get("light_sources")
            or []
        ),
        "software": copy.deepcopy(canonical_software),
        "routes": canonical_routes,
        "diagnostics": diagnostics,
    }

    dto["methods_generation"] = copy.deepcopy(inst.get("methods_generation") or {})
    dto["methods_view_dto"] = methods_view_dto

    # Runtime-selected optical truth is exported on the DTO and should be the
    # primary source for methods text when present. localStorage is fallback-only.
    dto["runtime_selected_configuration"] = (
        None
        if any(diagnostic.get("code") == "missing_selected_execution" for diagnostic in diagnostics)
        else copy.deepcopy(inst.get("runtime_selected_configuration"))
    )

    return dto


__all__ = [
    "build_methods_generator_page_config",
    "build_plan_experiments_page_config",
    "build_methods_generator_instrument_export",
]
