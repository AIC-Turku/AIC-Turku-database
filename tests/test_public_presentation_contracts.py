"""Presentation contracts for the public dashboard.

These cover defects that are only visible in a browser but are cheap to pin
down in the generated output: synthetic fixtures reaching public navigation,
generated navigation drifting from the source that produces it, empty sections
that read as broken pages, and ledger identifiers shown where a human label
exists.
"""

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader

from scripts.dashboard.loaders import (
    NonPublicInstrumentConfigError,
    load_facility_config,
    load_instruments,
    non_public_instrument_ids,
)
from scripts.dashboard.site_render import build_mkdocs_config, build_nav


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "dashboard_docs"


@pytest.fixture(scope="module", autouse=True)
def _generated_site() -> None:
    """`dashboard_docs/` and `mkdocs.yml` are generated, so build them here.

    CI runs the test suite before the dashboard build, so a fresh checkout has
    no generated output to assert against.
    """
    subprocess.run(
        [sys.executable, "-m", "scripts.dashboard_builder", "--strict"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )


def _template_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(REPO_ROOT / "scripts" / "templates"),
        autoescape=False,
    )


class NonPublicInstrumentTests(unittest.TestCase):
    """Records marked non-public must not reach the generated site."""

    def _facility(self) -> dict:
        return load_facility_config(REPO_ROOT).get("facility", {})

    def test_synthetic_fixture_is_declared_non_public(self) -> None:
        known = {"scope-testx1", "scope-real"}
        self.assertIn("scope-testx1", non_public_instrument_ids(self._facility(), known))

    def test_exclusions_must_be_known_unique_ids(self) -> None:
        for config in (
            {"non_public_instrument_ids": "scope-testx1"},
            {"non_public_instrument_ids": ["scope-missing"]},
            {"non_public_instrument_ids": ["scope-testx1", "scope-testx1"]},
        ):
            with self.subTest(config=config):
                with self.assertRaises(NonPublicInstrumentConfigError):
                    non_public_instrument_ids(config, {"scope-testx1"})

    def test_no_exclusions_configured_is_not_an_error(self) -> None:
        self.assertEqual(non_public_instrument_ids({}, {"scope-real"}), set())

    def test_fixture_is_absent_from_generated_navigation(self) -> None:
        nav = yaml.safe_load((REPO_ROOT / "mkdocs.yml").read_text(encoding="utf-8"))["nav"]
        self.assertNotIn("scope-testx1", yaml.safe_dump(nav))

    def test_fixture_has_no_generated_pages_or_event_pages(self) -> None:
        docs_root = DOCS_ROOT
        self.assertFalse((docs_root / "instruments" / "scope-testx1").exists())
        self.assertFalse((docs_root / "events" / "scope-testx1").exists())

    def test_fixture_is_absent_from_the_methods_generator_inventory(self) -> None:
        data = (DOCS_ROOT / "assets" / "instruments_data.json").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("scope-testx1", data)

    def test_one_authored_list_governs_the_site_and_the_catalogue(self) -> None:
        """A second exclusion list could drift and republish the fixture.

        The objective catalogue must honour the same withheld set the rest of
        the site uses, so there is nothing to keep in sync.
        """
        from scripts.dashboard.objective_catalogue import excluded_instruments

        known = {"scope-testx1", "scope-real"}
        self.assertEqual(
            excluded_instruments({"non_public_instrument_ids": ["scope-testx1"]}, known),
            {"scope-testx1"},
        )
        # A catalogue-only exclusion stays expressible alongside it.
        self.assertEqual(
            excluded_instruments(
                {
                    "non_public_instrument_ids": ["scope-testx1"],
                    "objective_catalogue": {"exclude_instrument_ids": ["scope-real"]},
                },
                known,
            ),
            {"scope-testx1", "scope-real"},
        )

    def test_catalogue_export_withholds_the_fixture(self) -> None:
        catalogue = json.loads(
            (DOCS_ROOT / "assets" / "objectives.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            [row for row in catalogue["items"] if row.get("instrument_id") == "scope-testx1"],
            [],
        )
        self.assertNotIn(
            "scope-testx1", {inst["id"] for inst in catalogue["instruments"]}
        )

    def test_fixture_record_is_still_present_for_tests(self) -> None:
        """The fixture is withheld from the site, not deleted from the ledger."""
        retired = load_instruments("instruments", include_retired=True)
        self.assertIn("scope-testx1", {inst["id"] for inst in retired})


class GeneratedNavigationTests(unittest.TestCase):
    """mkdocs.yml is generated, so its labels must come from build_nav()."""

    def test_generated_nav_matches_the_generator(self) -> None:
        """A hand-edit to mkdocs.yml is reverted by the next build, so the
        generator must already produce exactly what ships."""
        generated = yaml.safe_load((REPO_ROOT / "mkdocs.yml").read_text(encoding="utf-8"))
        withheld = non_public_instrument_ids(
            load_facility_config(REPO_ROOT).get("facility", {}),
            {
                inst["id"]
                for inst in load_instruments("instruments")
                + load_instruments("instruments", include_retired=True)
            },
        )
        instruments = [
            {"id": inst["id"], "display_name": inst["display_name"]}
            for inst in load_instruments("instruments")
            if inst["id"] not in withheld
        ]
        retired = [
            {"id": inst["id"], "display_name": inst["display_name"]}
            for inst in load_instruments("instruments", include_retired=True)
            if inst["id"] not in withheld
        ]
        self.assertEqual(generated["nav"], build_nav(instruments, retired))

    def test_top_level_labels_reproduce_the_facility_wording(self) -> None:
        """The generator must emit the labels the facility authored in a14e927.

        Sentence case was a deliberate editorial decision; regenerating Title
        Case silently undoes it on the next build.
        """
        labels = [next(iter(entry)) for entry in build_nav([], [])]
        self.assertEqual(
            labels,
            [
                "Fleet overview",
                "Instrument status",
                "Microscopes",
                "Objectives",
                "Experiment planning",
                "Virtual Microscope",
                "Methods generator",
                "Vocabulary dictionary",
                "Retired instruments",
            ],
        )

    def test_material_tabs_use_the_alternate_style(self) -> None:
        """Without alternate_style Material renders no tab bar and stacks panels."""
        config = build_mkdocs_config(
            facility={}, branding={}, instruments=[], retired_instruments=[]
        )
        tabbed = [
            extension
            for extension in config["markdown_extensions"]
            if isinstance(extension, dict) and "pymdownx.tabbed" in extension
        ]
        self.assertEqual(tabbed, [{"pymdownx.tabbed": {"alternate_style": True}}])

    def test_generated_config_on_disk_keeps_the_alternate_style(self) -> None:
        config = yaml.safe_load((REPO_ROOT / "mkdocs.yml").read_text(encoding="utf-8"))
        self.assertIn(
            {"pymdownx.tabbed": {"alternate_style": True}},
            config["markdown_extensions"],
        )


class EmptyStateTests(unittest.TestCase):
    """Empty sections must explain themselves rather than look broken."""

    def test_history_hides_the_qc_chart_section_without_chart_data(self) -> None:
        template = _template_env().get_template("instrument_history.md.j2")
        instrument = {"dto": {"identity": {"display_name": "Example"}}}

        without_charts = template.render(
            instrument=instrument,
            charts_json="{}",
            has_qc_charts=False,
            metric_names={},
            qc_events=[],
            maintenance_events=[],
        )
        self.assertNotIn("QC metrics over time", without_charts)
        self.assertIn("No events recorded yet", without_charts)

        with_charts = template.render(
            instrument=instrument,
            charts_json='{"metric": {}}',
            has_qc_charts=True,
            metric_names={},
            qc_events=[],
            maintenance_events=[],
        )
        self.assertIn("QC metrics over time", with_charts)

    def test_fleet_page_reports_an_empty_search_instead_of_blanking(self) -> None:
        index_md = (DOCS_ROOT / "index.md").read_text(encoding="utf-8")
        self.assertIn('id="aicNoResults"', index_md)
        self.assertIn("No microscopes match this search.", index_md)
        self.assertIn('id="aicResultCount"', index_md)


class InstrumentPagePresentationTests(unittest.TestCase):
    """Instrument pages must be identifiable and honest about availability."""

    def test_each_instrument_page_is_titled_with_its_own_name(self) -> None:
        pages = sorted((DOCS_ROOT / "instruments").glob("*/index.md"))
        self.assertTrue(pages)
        titles = set()
        for page in pages:
            first_lines = page.read_text(encoding="utf-8").splitlines()[:3]
            title_line = next(line for line in first_lines if line.startswith("title:"))
            title = title_line.split("title:", 1)[1].strip()
            self.assertNotEqual(title, "Instrument details")
            titles.add(title)
        self.assertEqual(len(titles), len(pages))

    def test_retired_pages_do_not_claim_to_be_online_or_link_the_simulator(self) -> None:
        page = (
            DOCS_ROOT
            / "instruments"
            / "scope-leica-tcs-sp5-multiphoton"
            / "index.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Retired from service", page)
        self.assertNotIn("🟢 Online", page)
        self.assertNotIn("Open Virtual Microscope", page)

    def test_active_pages_still_offer_the_simulator(self) -> None:
        page = (
            DOCS_ROOT / "instruments" / "scope-1e33f909" / "index.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Open Virtual Microscope", page)


class InternalLinkTests(unittest.TestCase):
    """Raw-HTML hrefs are not rewritten by MkDocs, so they must resolve as authored.

    Markdown links are rewritten relative to the SOURCE file; a hand-written
    <a href> in a template is resolved by the browser relative to the BUILT page
    URL. Mixing the two conventions in one template silently produces 404s, so
    every generated relative link is resolved here against the built tree.
    """

    def _built_site(self) -> Path:
        site = REPO_ROOT / "site"
        if not site.exists():
            subprocess.run(
                [sys.executable, "-m", "mkdocs", "build", "-q", "-d", str(site)],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
            )
        return site

    def test_every_relative_link_in_the_built_site_resolves(self) -> None:
        site = self._built_site()
        broken: list[str] = []
        for page in site.rglob("*.html"):
            if page.name == "404.html":
                continue  # 404.html intentionally uses absolute deploy-root paths
            html = page.read_text(encoding="utf-8", errors="replace")
            for raw in re.findall(r'(?:href|src)="([^"]+)"', html):
                if raw.startswith(("http://", "https://", "//", "#", "mailto:", "data:", "javascript:")):
                    continue
                target = unquote(urlparse(raw).path)
                if not target or target.startswith("/"):
                    continue
                resolved = (page.parent / target).resolve()
                if resolved.is_dir():
                    resolved = resolved / "index.html"
                if not resolved.exists():
                    broken.append(f"{page.relative_to(site)} -> {raw}")
        self.assertEqual(broken, [], f"{len(broken)} unresolved relative link(s): {broken[:10]}")


class DeveloperLanguageTests(unittest.TestCase):
    """Public pages should not expose repository paths or asset filenames."""

    def test_virtual_microscope_does_not_show_the_spectra_asset_path(self) -> None:
        """The path may appear as a fetch URL in script, never as visible copy."""
        page = (DOCS_ROOT / "virtual_microscope.md").read_text(
            encoding="utf-8"
        )
        subtitles = [
            line
            for line in page.splitlines()
            if "vm-search-box-subtitle" in line or "vm-chart-subtitle" in line
        ]
        self.assertTrue(subtitles)
        for line in subtitles:
            self.assertNotIn("assets/data/spectra", line)
        self.assertIn("Search the spectra bundled with this site.", page)

    def test_planning_download_button_is_not_labelled_with_a_filename(self) -> None:
        page = (DOCS_ROOT / "plan_experiments.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("[Download the facility inventory (JSON)]", page)
        self.assertNotIn("[Download `llm_inventory.json`]", page)

    def test_virtual_microscope_survives_a_missing_chart_library(self) -> None:
        app_js = (
            REPO_ROOT / "scripts" / "templates" / "virtual_microscope_app.js"
        ).read_text(encoding="utf-8")
        init_charts = app_js.split("function initCharts()", 1)[1].split("}", 1)[0]
        self.assertIn("typeof Chart === 'undefined'", init_charts)

        page = (DOCS_ROOT / "virtual_microscope.md").read_text(
            encoding="utf-8"
        )
        self.assertIn('id="vm-charts-unavailable"', page)


if __name__ == "__main__":
    unittest.main()
