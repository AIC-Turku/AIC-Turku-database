import unittest
from pathlib import Path


class VirtualMicroscopeAppTemplateTests(unittest.TestCase):
    def test_app_uses_pipe_as_the_single_route_ui(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertNotIn("function buildAuthoritativeRouteGraph(topology)", source)
        self.assertNotIn("function renderAuthoritativeRouteGraph(host, graphModel)", source)
        self.assertNotIn("const authoritativeGraph = buildAuthoritativeRouteGraph(topology);", source)
        self.assertNotIn("renderAuthoritativeRouteGraph(topologyWrap, authoritativeGraph);", source)
        self.assertIn("const derivedControlGroups = buildDerivedControlGroups(inst, topology, route);", source)
        self.assertIn("shell.appendChild(pipeline);", source)
        self.assertIn("shell.appendChild(inspector);", source)

    def test_route_traversal_uses_authoritative_route_steps_without_sequence_fallback(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("route_steps", source)
        self.assertIn("active route is missing authoritative route_steps", source)
        self.assertIn("function authoritativeRouteSteps(routeRecord)", source)
        self.assertIn("const selectedExecution = routeRecord && routeRecord.record && routeRecord.record.selected_execution;", source)
        self.assertIn("const selectedSteps = Array.isArray(selectedExecution && selectedExecution.steps) ? selectedExecution.steps : [];", source)
        self.assertIn("if (selectedSteps.length) return selectedSteps;", source)
        self.assertNotIn("buildPhase((routeRecord && (routeRecord.record && routeRecord.record.illumination_sequence))", source)
        self.assertNotIn("buildPhase((routeRecord && (routeRecord.record && routeRecord.record.detection_sequence))", source)

    def test_pipeline_ui_is_built_from_route_traversal(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("function buildPipelineStages(topology)", source)
        self.assertIn("const pipelineStages = buildPipelineStages(topology);", source)
        self.assertIn("pipeline.style.display = pipelineStages.length ? 'flex' : 'none';", source)
        self.assertIn("createPipeSegment(stagePipeKey(pipelineStages[index - 1].flowOrigin, stage.flowOrigin))", source)
        self.assertIn("createPipelineBadge(stage.id, stage.label, stage.inspectorStage)", source)

    def test_pipeline_beam_colors_use_per_step_spectra(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("function pipelineSpectrumForStep(stepId, stepSpectra, fallbackSpectra)", source)
        self.assertIn("function buildStepSpectra(selection, grid, sourceMixed, generatedEmission, simulation)", source)
        self.assertIn("setPipeSpectrumColor(key, pipelineSpectrumForStep(fromNode, stepSpectra, fallbackSpectra), grid);", source)
        self.assertIn("const illuminationComponents = Array.isArray(selection && selection.illuminationComponents) ? selection.illuminationComponents : [];", source)
        self.assertIn("const detectionComponents = Array.isArray(selection && selection.detectionComponents) ? selection.detectionComponents : [];", source)
        self.assertIn("if (!step || step.kind !== 'routing_component') return;", source)
        self.assertIn("stepSpectra.set(stepId, routedBranchSpectrum);", source)
        self.assertNotIn("const consumed = { excitation: 0, dichroic: 0, emission: 0 };", source)

    def test_source_settings_are_keyed_by_instrument_and_source_identity(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("currentInstrumentId || 'scope'", source)
        self.assertIn("source.id || source.inventory_id || source.hardware_inventory_id", source)
        self.assertIn("normalizeSourceRoutes(source).join('|') || 'any-route'", source)

    def test_pipeline_layout_wraps_to_new_row_when_badges_overflow(self) -> None:
        source = Path("scripts/templates/virtual_microscope.html.j2").read_text(encoding="utf-8")
        self.assertIn("flex-wrap: wrap;", source)

    def test_pipe_buttons_use_route_traversal_entries(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("topology && topology.traversal && Array.isArray(topology.traversal.illumination)", source)
        self.assertIn("topology && topology.traversal && Array.isArray(topology.traversal.detection)", source)
        self.assertIn("button.dataset.inspectorStage = inspectorStage || stageId;", source)
        self.assertIn("button.dataset.inspectorStage || button.dataset.stageId", source)

    def test_pipe_stages_use_unique_keys(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("key: 'pipe:sources:0'", source)
        self.assertIn("key: 'pipe:illumination:' + index", source)
        self.assertIn("key: 'pipe:sample:0'", source)
        self.assertIn("key: 'pipe:detection:' + index", source)
        self.assertIn("key: 'pipe:detectors:0'", source)

    def test_transmitted_route_detection_covers_all_transmitted_tags(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("'transmitted_brightfield'", source)
        self.assertIn("'phase_contrast'", source)
        self.assertIn("'darkfield'", source)
        self.assertIn("'dic'", source)
        self.assertNotIn(
            "route === 'transmitted' || route === 'brightfield' || route === 'phase'",
            source,
            "Old 3-route transmitted check should be replaced with comprehensive list",
        )

    def test_active_route_order_uses_runtime_sort_order(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("VM.ROUTE_SORT_ORDER", source)
        self.assertNotIn(
            "return ['confocal', 'epi', 'tirf', 'multiphoton', 'transmitted'];",
            source,
            "Old 5-route hardcoded order should be replaced",
        )

    def test_pipe_no_longer_invents_generic_illumination_or_detection_controls(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertNotIn("id: 'illumination-controls'", source)
        self.assertNotIn("label: 'Illumination Controls'", source)
        self.assertNotIn("id: 'detection-controls'", source)
        self.assertNotIn("label: 'Detection Controls'", source)

    def test_traversal_entries_use_parser_step_ids(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("routeStepId: step.step_id", source)
        self.assertNotIn("function assignRouteStepIds(entries, phase)", source)

    def test_pipe_stages_use_route_step_ids(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("entry.routeStepId || ('illumination-step-' + index)", source)
        self.assertIn("entry.routeStepId || ('detection-step-' + index)", source)

    def test_derived_control_groups_use_parser_step_ids(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertNotIn("id: 'illumination-controls'", source)
        self.assertIn("const stepId = entry.routeStepId", source)

    def test_pipeline_stages_render_from_topology_not_derived_groups(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("function buildPipelineStages(topology)", source)
        self.assertNotIn("function buildPipelineStages(derivedControlGroups", source)
        self.assertIn("topology.sourceMechanisms", source)
        self.assertIn("topology.endpointMechanisms", source)

    def test_endpoint_entries_excluded_from_detection_traversal_stages(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("entry.kind === 'endpoint'", source)
        pipe_fn = source.split("function buildPipelineStages")[1].split("\n  function ")[0]
        self.assertIn("if (entry.kind === 'endpoint') return;", pipe_fn)
        groups_fn = source.split("function buildDerivedControlGroups")[1].split("\n  function ")[0]
        self.assertIn("entry.kind === 'branch-block' || entry.kind === 'endpoint'", groups_fn)

    def test_pipe_stages_use_step_id_as_flow_origin(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        pipe_fn = source.split("function buildPipelineStages")[1].split("\n  function ")[0]
        self.assertIn("flowOrigin: stepId", pipe_fn)
        self.assertIn("label: entry.kind === 'branch-block' ? 'Routing' : (entry.title || 'Detection')", pipe_fn)
        self.assertNotIn("flowOrigin: 'illumination'", pipe_fn)
        self.assertNotIn("flowOrigin: 'detection'", pipe_fn)

    def test_no_bucket_based_flow_origin_normalization(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertNotIn("function pipelineFlowOrigin(", source)
        self.assertNotIn("function pipelineSpectrumForOrigin(", source)

    def test_selection_includes_traversal_ordered_components(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("function buildTraversalOrderedComponents(topology, selection, phase)", source)
        self.assertIn("selection.illuminationComponents = buildTraversalOrderedComponents(topology, selection, 'illumination')", source)
        self.assertIn("selection.detectionComponents = buildTraversalOrderedComponents(topology, selection, 'detection')", source)
        self.assertIn("selectedComponentByMechanism", source)
        self.assertIn("const mechanismByStepId = new Map();", source)
        self.assertIn("mechanismByStepId.set(entry.routeStepId", source)
        self.assertIn("step_id", source)

    def test_simulation_uses_traversal_ordered_components(self) -> None:
        source = Path("scripts/templates/virtual_microscope_runtime.js").read_text(encoding="utf-8")

        self.assertIn("selected.illuminationComponents", source)
        self.assertIn("selected.detectionComponents", source)
        self.assertIn("illuminationOrdered", source)
        self.assertIn("detectionOrdered", source)

    def test_expand_cube_selection_warns_on_incomplete_cubes(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("cubePosition._cube_incomplete", source)
        self.assertIn("has no explicit excitation filter data", source)

    def test_filter_cube_component_mask_fallback_removed(self) -> None:
        source = Path("scripts/templates/virtual_microscope_runtime.js").read_text(encoding="utf-8")

        self.assertNotIn("if (type === 'filter_cube')", source)

    # ── VM-005: composite cube in componentMask ─────────────────────────

    def test_filter_cube_component_mask_uses_linked_sub_components(self) -> None:
        source = Path("scripts/templates/virtual_microscope_runtime.js").read_text(encoding="utf-8")

        self.assertIn("component.spectral_ops", source)
        self.assertIn("missing parser spectral_ops", source)
        self.assertNotIn("has no linked sub-components", source)

    # ── VM-006: unsupported component warnings ──────────────────────────

    def test_analyzer_handling_is_parser_driven(self) -> None:
        source = Path("scripts/templates/virtual_microscope_runtime.js").read_text(encoding="utf-8")

        self.assertIn("component.spectral_ops", source)
        self.assertNotIn("type === 'analyzer'", source)

    def test_unknown_type_no_longer_warns_in_runtime(self) -> None:
        source = Path("scripts/templates/virtual_microscope_runtime.js").read_text(encoding="utf-8")

        self.assertNotIn("unsupported component type", source)

    # ── VM-006: analyzer stage in deriveStageGroupAdapters ──

    def test_analyzer_stage_in_derive_stage_group_adapters(self) -> None:
        source = Path("scripts/templates/virtual_microscope_runtime.js").read_text(encoding="utf-8")

        self.assertIn("analyzer: normalizeMechanismList(stageSource && stageSource.analyzer)", source)

    def test_analyzer_field_in_normalized_instrument(self) -> None:
        source = Path("scripts/templates/virtual_microscope_runtime.js").read_text(encoding="utf-8")

        self.assertIn("analyzer: derivedStageAdapters.stages.analyzer", source)

    # ── VM-007: sequential acquisition detection ──

    def test_requires_sequential_acquisition_in_optimizer(self) -> None:
        source = Path("scripts/templates/virtual_microscope_runtime.js").read_text(encoding="utf-8")

        self.assertIn("requiresSequentialAcquisition", source)
        self.assertIn("perFluorophoreConfigs", source)
        self.assertIn("sequentialPlan", source)

    def test_run_auto_configure_handles_sequential(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("result.requiresSequentialAcquisition", source)
        self.assertIn("function renderSequentialAcquisitionPlan(steps, activeStepIndex = null)", source)
        self.assertIn("button.textContent = activeStepIndex === index ? 'Applied' : `Apply step ${entry.step || (index + 1)}`;", source)
        self.assertIn("applyOptimizedConfiguration(steps[0].configuration);", source)
        self.assertIn("renderSequentialAcquisitionPlan(steps, 0);", source)

    # ── VM-008: deduplicated detector legends ──

    def test_detector_legend_deduplication_in_propagation_panel(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("seenDetectorLabels", source)

    # ── VM-009: chart scaling uses suggestedMax instead of hard max ──

    def test_chart_y_axis_uses_suggested_max(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("suggestedMax: 105", source)
        self.assertNotIn("max: 105", source)

    def test_chart_dataset_no_hard_clip(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertNotIn("Math.min(105,", source)

    # ── VM-010: unsupported spectral model surfaced in UI metadata ──

    def test_unsupported_spectral_model_in_format_component_metadata(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("_unsupported_spectral_model", source)
        self.assertIn("Spectral model not available", source)
        self.assertIn("_cube_incomplete", source)
        self.assertIn("exact spectral simulation and optimization may be unavailable", source)

    # ── VM-011: buildSelectedConfiguration function exists ──

    def test_build_selected_configuration_function_exists(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("function buildSelectedConfiguration(", source)
        self.assertIn("selectionMap", source)
        self.assertIn("scope_id", source)
        self.assertIn("acquisition_plan", source)
        self.assertIn("_cube_incomplete", source)

    def test_selected_configuration_is_computed_on_every_refresh(self) -> None:
        """buildSelectedConfiguration must be called in refreshOutputs so the config is always current."""
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("state.lastSelectedConfiguration = buildSelectedConfiguration(selection, simulation);", source)
        self.assertIn("state.lastSelectedConfiguration = buildSelectedConfiguration(repairedSelection, simulation);", source)

    def test_selected_configuration_exposed_via_public_api(self) -> None:
        """External consumers must be able to access the selected configuration."""
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("window.getVirtualMicroscopeConfiguration", source)
        self.assertIn("state.lastSelectedConfiguration", source)
        self.assertIn("persistSelectedConfiguration", source)
        self.assertIn("aic.virtualMicroscope.selectedConfiguration", source)

    def test_refresh_outputs_catches_simulation_errors_and_sets_inline_status(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("console.error('Failed to refresh simulation outputs', error);", source)
        self.assertIn("const message = `Error loading fluorophore: ${errorMessage(error)}`;", source)
        self.assertIn("setInlineStatus(DOM.searchStatus, message, 'error');", source)
        self.assertIn("setInlineStatus(DOM.localSearchStatus, message, 'error');", source)

    # ── Stage adapter comment accuracy ──

    def test_stage_adapters_no_longer_document_fallback_roles(self) -> None:
        source = Path("scripts/templates/virtual_microscope_runtime.js").read_text(encoding="utf-8")

        self.assertNotIn("fallbacks when route topology", source)

    def test_execute_spectral_ops_functions_are_exported(self) -> None:
        """The runtime must export executeSpectralOps and executeSingleSpectralOp."""
        source = Path("scripts/templates/virtual_microscope_runtime.js").read_text(encoding="utf-8")
        self.assertIn("executeSpectralOps", source)
        self.assertIn("executeSingleSpectralOp", source)

    def test_component_mask_prefers_spectral_ops(self) -> None:
        """componentMask should check for spectral_ops before type-based interpretation."""
        source = Path("scripts/templates/virtual_microscope_runtime.js").read_text(encoding="utf-8")
        self.assertIn("component.spectral_ops", source)

    def test_source_centers_does_not_parse_display_label(self) -> None:
        """sourceCenters must not parse wavelengths from display_label."""
        source = Path("scripts/templates/virtual_microscope_runtime.js").read_text(encoding="utf-8")
        # The old block parsed source.display_label, source.name, source.model, etc.
        self.assertNotIn("source.display_label,\n      source && source.name,", source)

    def test_parser_spectral_ops_present_in_component_payload(self) -> None:
        """_component_payload should include spectral_ops."""
        source = Path("scripts/light_path_parser.py").read_text(encoding="utf-8")
        self.assertIn("_spectral_ops_for_component", source)
        self.assertIn('"spectral_ops"', source)


if __name__ == "__main__":
    unittest.main()
