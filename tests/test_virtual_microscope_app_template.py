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
        self.assertIn("const selectedRouteSteps = Array.isArray(selectedExecution && selectedExecution.selected_route_steps) ? selectedExecution.selected_route_steps : [];", source)
        self.assertIn("if (selectedRouteSteps.length) return selectedRouteSteps;", source)
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
        self.assertIn("const beamState = buildStepSpectra(selection, grid, sourceMixed, generatedEmission, simulation);", source)
        self.assertIn("const stepSpectra = beamState && beamState.stepSpectra instanceof Map ? beamState.stepSpectra : new Map();", source)
        self.assertIn("setPipeSpectrumColor(key, spectrum, grid);", source)
        self.assertIn("const resolvedExecution = Array.isArray(selection && selection.resolvedExecution) ? selection.resolvedExecution : [];", source)
        self.assertIn("step.kind === 'routing_component'", source)
        self.assertIn("stepSpectra.set(stepId, runningDetect.slice());", source)
        self.assertIn("unsupportedActiveTraversal: untrustworthyStepIds.size > 0,", source)
        self.assertNotIn("const consumed = { excitation: 0, dichroic: 0, emission: 0 };", source)
        self.assertNotIn("if (stageKey === 'splitters') return;", source)

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

        # buildPipelineStages now reads route steps directly; traversal is used by buildDerivedControlGroups
        self.assertIn("authoritativeRouteSteps(routeRecord)", source)
        self.assertIn("button.dataset.inspectorStage = inspectorStage || stageId;", source)
        self.assertIn("button.dataset.inspectorStage || button.dataset.stageId", source)

    def test_pipe_stages_use_unique_keys(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("key: 'pipe:sources:0'", source)
        self.assertIn("key: 'pipe:illumination:' + illumIndex", source)
        self.assertIn("key: 'pipe:sample:0'", source)
        self.assertIn("key: 'pipe:detection:' + detectIndex", source)
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

        # buildPipelineStages reads step.step_id from route steps directly
        pipe_fn = source.split("function buildPipelineStages")[1].split("\n  function ")[0]
        self.assertIn("cleanString(step.step_id)", pipe_fn)
        # buildRouteTraversalEntries still uses parser step_ids for traversal entries
        self.assertIn("routeStepId: step.step_id", source)

    def test_derived_control_groups_use_parser_step_ids(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertNotIn("id: 'illumination-controls'", source)
        self.assertIn("const stepId = entry.routeStepId", source)

    def test_pipeline_stages_render_from_topology_not_derived_groups(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("function buildPipelineStages(topology)", source)
        self.assertNotIn("function buildPipelineStages(derivedControlGroups", source)
        # Pipe stages now read route steps via authoritativeRouteSteps, not traversal or mechanism lists
        pipe_fn = source.split("function buildPipelineStages")[1].split("\n  function ")[0]
        self.assertIn("authoritativeRouteSteps(routeRecord)", pipe_fn)
        self.assertNotIn("topology.traversal", pipe_fn)

    def test_endpoint_entries_excluded_from_detection_traversal_stages(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        # buildPipelineStages excludes detectors via step.kind !== 'detector' filter
        pipe_fn = source.split("function buildPipelineStages")[1].split("\n  function ")[0]
        self.assertIn("step.kind !== 'detector'", pipe_fn)
        # buildDerivedControlGroups still excludes branch-block and endpoint entries
        groups_fn = source.split("function buildDerivedControlGroups")[1].split("\n  function ")[0]
        self.assertIn("entry.kind !== 'detector' && entry.kind !== 'endpoint'", groups_fn)

    def test_pipe_stages_use_step_id_as_flow_origin(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        pipe_fn = source.split("function buildPipelineStages")[1].split("\n  function ")[0]
        self.assertIn("flowOrigin: stepId", pipe_fn)
        self.assertIn("step.kind === 'routing_component' ? 'Routing'", pipe_fn)
        self.assertNotIn("flowOrigin: 'illumination'", pipe_fn)
        self.assertNotIn("flowOrigin: 'detection'", pipe_fn)

    def test_no_bucket_based_flow_origin_normalization(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertNotIn("function pipelineFlowOrigin(", source)
        self.assertNotIn("function pipelineSpectrumForOrigin(", source)

    def test_selection_includes_traversal_ordered_components(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("function resolveSelectedExecution(selectedRouteSteps, mechanismSelections)", source)
        self.assertIn("function orderedComponentsFromExecution(resolvedSteps, phase, splitterSelections = new Map())", source)
        self.assertIn("selection.resolvedExecution = resolveSelectedExecution(selectedRouteSteps, selection.selectedComponentByMechanism)", source)
        self.assertIn("selection.illuminationComponents = orderedComponentsFromExecution(selection.resolvedExecution, 'illumination')", source)
        self.assertIn("selection.detectionComponents = orderedComponentsFromExecution(selection.resolvedExecution, 'detection')", source)
        self.assertIn("selectedComponentByMechanism", source)
        self.assertNotIn("function buildTraversalOrderedComponents(", source)
        self.assertIn("step_id", source)

        ordered_fn = source.split("function orderedComponentsFromExecution")[1].split("\n  function ")[0]
        self.assertIn("stageKey === 'splitter'", ordered_fn)
        self.assertIn("componentType === 'splitter'", ordered_fn)
        self.assertIn("stageKey === 'port_selector'", ordered_fn)
        self.assertIn("componentType === 'port_selector'", ordered_fn)
        self.assertIn("stageKey === 'route_control'", ordered_fn)
        self.assertIn("componentType === 'route_control'", ordered_fn)
        self.assertIn("normalizedStepType === 'splitter'", ordered_fn)
        self.assertIn("normalizedStepType === 'port_selector'", ordered_fn)
        self.assertIn("normalizedStepType === 'route_control'", ordered_fn)
        self.assertIn("resolvedStageKey === 'splitter'", ordered_fn)
        self.assertIn("resolvedType === 'splitter'", ordered_fn)
        self.assertIn("resolvedStageKey === 'port_selector'", ordered_fn)
        self.assertIn("resolvedType === 'port_selector'", ordered_fn)
        self.assertIn("resolvedStageKey === 'route_control'", ordered_fn)
        self.assertIn("resolvedType === 'route_control'", ordered_fn)
        self.assertIn("if (!(component && component.spectral_ops && typeof component.spectral_ops === 'object')) return;", ordered_fn)

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

    def test_cube_ui_helpers_use_only_canonical_parser_field_names(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        expand_fn = source.split("function expandCubeSelection")[1].split("\n  function ")[0]
        self.assertIn("cubePosition.excitation_filter", expand_fn)
        self.assertIn("cubePosition.dichroic", expand_fn)
        self.assertIn("cubePosition.emission_filter", expand_fn)
        self.assertNotRegex(expand_fn, r"cubePosition\.(?:ex|excitation|di|dichroic_filter|em|emission)\b")

        notes_fn = source.split("function appendLinkedCubeNotes")[1].split("\n  function ")[0]
        self.assertIn("cubeValue.dichroic", notes_fn)
        self.assertIn("cubeValue.emission_filter", notes_fn)
        self.assertNotRegex(notes_fn, r"cubeValue\.(?:di|dichroic_filter|em|emission)\b")

    def test_unresolved_selected_execution_uses_available_position_spectral_ops(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        resolve_fn = source.split("function resolveSelectedExecution")[1].split("\n  function ")[0]
        self.assertIn("const candidates = Array.isArray(step.available_positions) ? step.available_positions : [];", resolve_fn)
        self.assertIn("candidates.find((cand) => cleanString(cand.position_key) === positionKey)", resolve_fn)
        self.assertIn("const resolvedOps = (matched && matched.spectral_ops) || selectedComponent.spectral_ops || null;", resolve_fn)
        self.assertIn("spectral_ops: resolvedOps,", resolve_fn)
        self.assertNotIn("center_nm", resolve_fn)
        self.assertNotIn("cut_on_nm", resolve_fn)
        self.assertNotIn("cut_off_nm", resolve_fn)
        self.assertNotIn("bands:", resolve_fn)
        self.assertNotIn("transmission_bands", resolve_fn)
        self.assertNotIn("reflection_bands", resolve_fn)

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

    def test_run_auto_configure_surfaces_unsupported_and_optimizer_errors(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        run_auto_fn = source.split("function runAutoConfigure()")[1].split("\n  function ")[0]
        self.assertIn("selection = collectRuntimeSelection();", run_auto_fn)
        self.assertIn("const unsupportedIssues = unsupportedTraversalIssues(selection);", run_auto_fn)
        self.assertIn("Auto-configure unavailable: active route contains unsupported parser optics", run_auto_fn)
        self.assertIn("result = VM.optimizeLightPath", run_auto_fn)
        self.assertIn("catch (error)", run_auto_fn)
        self.assertIn("setStatusMessage(`Auto-configure failed: ${errorMessage(error)}`, 'error');", run_auto_fn)
        self.assertIn("if (result && result.unsupported)", run_auto_fn)
        self.assertIn("applyOptimizedConfiguration(result);", run_auto_fn)

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

    def test_safe_component_mask_helper_only_degrades_missing_parser_spectral_ops(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("function safeComponentMask(component, grid, options = {}, context = {})", source)
        self.assertIn("reason: 'missing_spectral_ops'", source)
        self.assertIn("if (component && typeof component === 'object' && !component.spectral_ops)", source)
        self.assertIn("if (cleanString(errorMessage(error)).includes('missing parser spectral_ops'))", source)
        self.assertIn("throw error;", source)

    def test_chart_masks_use_safe_component_mask_and_warn_inline(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        overlays_fn = source.split("function activeFilterMaskDatasets")[1].split("\n  function ")[0]
        self.assertIn("const overlayWarnings = [];", overlays_fn)
        self.assertIn("const result = safeComponentMask(component, grid, { mode }", overlays_fn)
        self.assertIn("overlayWarnings.push(result.issue);", overlays_fn)
        self.assertIn("Skipping chart overlays for unsupported parser payloads", overlays_fn)

        combined_fn = source.split("function combinedMask")[1].split("\n  function ")[0]
        self.assertIn("fallbackMode: 'passthrough'", combined_fn)
        self.assertIn("return { mask, issues };", combined_fn)

        reference_fn = source.split("function renderReferenceSpectra")[1].split("\n  function ")[0]
        self.assertIn("const excitationMaskResult = combinedMask", reference_fn)
        self.assertIn("Reference spectra warning:", reference_fn)
        self.assertIn("missing parser spectral_ops.", reference_fn)

        propagation_fn = source.split("function renderPropagationPanel")[1].split("\n  function ")[0]
        self.assertIn("const emissionMaskResult = combinedMask", propagation_fn)
        self.assertIn("Collection warning:", propagation_fn)
        self.assertIn("missing parser spectral_ops.", propagation_fn)

    def test_optimizer_excludes_missing_ops_options_from_ranking(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        apply_fn = source.split("function applyComponentsToSpectrum")[1].split("\n  function ")[0]
        self.assertIn("const result = safeComponentMask(component, grid, { mode }", apply_fn)
        self.assertIn("unsupported: issues.length > 0", apply_fn)

        score_fn = source.split("function scoreStageOption")[1].split("\n  function ")[0]
        self.assertIn("if (output.unsupported) return Number.NEGATIVE_INFINITY;", score_fn)

        repair_fn = source.split("function autoRepairBlockedPath")[1].split("\n  function ")[0]
        self.assertIn("Optimizer skipped unsupported parser payload:", repair_fn)

    def test_selection_components_keep_stage_and_mechanism_metadata_for_missing_ops_warnings(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("_maskStage: stage", source)
        self.assertIn("_maskMechanismName: name", source)
        self.assertIn("_maskMechanismName: mechanismName", source)

    def test_missing_spectral_ops_path_degrades_gracefully_instead_of_crashing(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        safe_mask_fn = source.split("function safeComponentMask")[1].split("\n  function ")[0]
        self.assertIn("if (component && typeof component === 'object' && !component.spectral_ops) {", safe_mask_fn)
        self.assertIn("return warnMissingOps();", safe_mask_fn)
        self.assertIn("return warnMissingOps(error);", safe_mask_fn)
        self.assertIn("throw error;", safe_mask_fn)

        overlays_fn = source.split("function activeFilterMaskDatasets")[1].split("\n  function ")[0]
        self.assertIn("if (!result.ok && result.reason === 'missing_spectral_ops') {", overlays_fn)
        self.assertIn("overlayWarnings.push(result.issue);", overlays_fn)
        self.assertIn("return;", overlays_fn)

        combined_fn = source.split("function combinedMask")[1].split("\n  function ")[0]
        self.assertIn("if (!result.ok && result.reason === 'missing_spectral_ops') {", combined_fn)
        self.assertIn("issues.push(result.issue);", combined_fn)
        self.assertIn("return accumulator;", combined_fn)
        self.assertIn("return { mask, issues };", combined_fn)

    def test_blocked_pipeline_paths_blank_downstream_colors(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        update_fn = source.split("function updatePipelineBeamColors")[1].split("\n  function ")[0]
        self.assertIn("simulation && simulation.simulationError", update_fn)
        self.assertIn("simulation && simulation.validSelection === false", update_fn)
        self.assertIn("simulation && simulation.routeViolation", update_fn)
        self.assertIn("setPipeSpectrumColor(key, fallbackSpectra.empty, grid);", update_fn)
        self.assertIn("!spectrumHasMeaningfulThroughput(spectrum)", update_fn)

    def test_unsupported_cube_stops_exact_downstream_beam_coloring(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        build_fn = source.split("function buildStepSpectra")[1].split("\n  function ")[0]
        self.assertIn("function stepHasUnsupportedOptics(step)", build_fn)
        self.assertIn("step._cube_incomplete", build_fn)
        self.assertIn("step._unsupported_spectral_model", build_fn)
        self.assertIn("!(component && component.spectral_ops)", build_fn)
        self.assertIn("runningIllum = emptySpectrum.slice();", build_fn)
        self.assertIn("stepSpectra.set('sample', emptySpectrum.slice());", build_fn)
        self.assertIn("stepSpectra.set('detectors', detectionTrustBroken ? emptySpectrum.slice() : detectorSpectrum);", build_fn)

    def test_valid_pipeline_paths_still_render_normal_colors(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        update_fn = source.split("function updatePipelineBeamColors")[1].split("\n  function ")[0]
        self.assertIn("const spectrum = shouldBlankAll", update_fn)
        self.assertIn("setPipeSpectrumColor(key, spectrum, grid);", update_fn)
        self.assertIn("|| !spectrumHasMeaningfulThroughput(spectrum)", update_fn)

    # ── VM-011: buildSelectedConfiguration function exists ──

    def test_build_selected_configuration_function_exists(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("function buildSelectedConfiguration(", source)
        self.assertIn("selectionMap", source)
        self.assertIn("scope_id", source)
        self.assertIn("acquisition_plan", source)
        self.assertIn("_cube_incomplete", source)

    def test_selected_configuration_uses_resolved_execution(self) -> None:
        """buildSelectedConfiguration must source from resolvedExecution, not debugSelections."""
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        config_fn = source[source.index("function buildSelectedConfiguration("):source.index("function buildSelectedConfiguration(") + 3000]
        self.assertIn("selection.resolvedExecution", config_fn)
        self.assertIn("selected_route_steps:", config_fn)
        self.assertNotIn("selection.debugSelections", config_fn)
        self.assertNotIn("stages:", config_fn)

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
        self.assertIn("const message = `Error simulating instrument: ${errorMessage(error)}`;", source)
        self.assertIn("setInlineStatus(DOM.searchStatus, message, 'error');", source)
        self.assertIn("setInlineStatus(DOM.localSearchStatus, message, 'error');", source)
        self.assertIn("simulationError: true,", source)
        self.assertIn("simulationErrorMessage: errorMessage(error),", source)

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
