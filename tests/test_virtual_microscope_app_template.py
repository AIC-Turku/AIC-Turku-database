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

    def test_route_traversal_falls_back_to_canonical_sequences_when_resolved_arrays_are_empty(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("const resolvedIlluminationTraversal = Array.isArray(routeRecord && routeRecord.illuminationTraversal) && routeRecord.illuminationTraversal.length", source)
        self.assertIn("const resolvedDetectionTraversal = Array.isArray(routeRecord && routeRecord.detectionTraversal) && routeRecord.detectionTraversal.length", source)
        self.assertIn("buildPhase((routeRecord && (routeRecord.record && routeRecord.record.illumination_sequence))", source)
        self.assertIn("buildPhase((routeRecord && (routeRecord.record && routeRecord.record.detection_sequence))", source)

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
        self.assertIn("function buildStepSpectra(selection, grid, sourceMixed, generatedEmission)", source)
        self.assertIn("setPipeSpectrumColor(key, pipelineSpectrumForStep(fromNode, stepSpectra, fallbackSpectra), grid);", source)

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

    def test_traversal_entries_receive_stable_route_step_ids(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("function assignRouteStepIds(entries, phase)", source)
        self.assertIn("entry.routeStepId = `${phase}-step-${stepIndex}`", source)
        self.assertIn("assignRouteStepIds(result.illumination, 'illumination')", source)
        self.assertIn("assignRouteStepIds(result.detection, 'detection')", source)

    def test_pipe_stages_use_route_step_ids(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("entry.routeStepId || ('illumination-step-' + index)", source)
        self.assertIn("entry.routeStepId || ('detection-step-' + index)", source)

    def test_derived_control_groups_use_per_entry_illumination_groups(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertNotIn("id: 'illumination-controls'", source)
        self.assertIn("entry.routeStepId || ('illumination-step-' + illumStepIndex)", source)
        self.assertIn("entry.routeStepId || ('detection-step-' + detStepIndex)", source)

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
        self.assertIn("entry.kind === 'branch-block' || entry.kind === 'endpoint'", pipe_fn)
        groups_fn = source.split("function buildDerivedControlGroups")[1].split("\n  function ")[0]
        self.assertIn("entry.kind === 'branch-block' || entry.kind === 'endpoint'", groups_fn)

    def test_pipe_stages_use_step_id_as_flow_origin(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        pipe_fn = source.split("function buildPipelineStages")[1].split("\n  function ")[0]
        self.assertIn("flowOrigin: stepId", pipe_fn)
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

    def test_simulation_uses_traversal_ordered_components(self) -> None:
        source = Path("scripts/templates/virtual_microscope_runtime.js").read_text(encoding="utf-8")

        self.assertIn("selected.illuminationComponents", source)
        self.assertIn("selected.detectionComponents", source)
        self.assertIn("illuminationOrdered", source)
        self.assertIn("detectionOrdered", source)


if __name__ == "__main__":
    unittest.main()
