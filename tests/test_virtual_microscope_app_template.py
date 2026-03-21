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

        self.assertIn("function buildPipelineStages(derivedControlGroups, topology)", source)
        self.assertIn("const pipelineStages = buildPipelineStages(derivedControlGroups, topology);", source)
        self.assertIn("pipeline.style.display = pipelineStages.length ? 'flex' : 'none';", source)
        self.assertIn("createPipeSegment(stagePipeKey(pipelineStages[index - 1].flowOrigin, stage.flowOrigin))", source)
        self.assertIn("createPipelineBadge(stage.id, stage.label, stage.inspectorStage)", source)

    def test_pipeline_beam_colors_support_group_level_stage_ids(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("function pipelineSpectrumForOrigin(origin, spectra)", source)
        self.assertIn("normalized === 'illumination-controls'", source)
        self.assertIn("normalized === 'detection-controls'", source)
        self.assertIn("setPipeSpectrumColor(key, pipelineSpectrumForOrigin(fromNode, spectra), grid);", source)

    def test_source_settings_are_keyed_by_instrument_and_source_identity(self) -> None:
        source = Path("scripts/templates/virtual_microscope_app.js").read_text(encoding="utf-8")

        self.assertIn("currentInstrumentId || 'scope'", source)
        self.assertIn("source.id || source.inventory_id || source.hardware_inventory_id", source)
        self.assertIn("normalizeSourceRoutes(source).join('|') || 'any-route'", source)

    def test_pipeline_layout_stays_on_one_line(self) -> None:
        source = Path("scripts/templates/virtual_microscope.html.j2").read_text(encoding="utf-8")
        self.assertIn("flex-wrap: nowrap;", source)

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


if __name__ == "__main__":
    unittest.main()
