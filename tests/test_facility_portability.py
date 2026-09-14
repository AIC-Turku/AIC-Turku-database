"""Portability boundaries between the project and the facility deploying it.

The README promises that another facility can reuse this project by editing
`facility.yaml` and its YAML records rather than Python or JavaScript. These
tests pin the boundaries that promise depends on:

- generated pages address the facility named in configuration, not AIC;
- a complete site builds from a synthetic second facility's data alone;
- conditional acknowledgements are bound to recorded instrument IDs rather than
  to instrument names a frontend has to recognise;
- deployment and fallback behaviour still honor authored facility configuration.

The synthetic facility lives in `tests/fixtures/example_facility/` and is
assembled into a temporary directory. It is never part of the production
instrument ledger.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pytest
import yaml

from scripts.dashboard.loaders import (
    DEFAULT_FACILITY_SHORT_NAME,
    facility_short_name,
    load_facility_config,
)
from scripts.dashboard.methods_export import (
    AcknowledgementConfigError,
    build_methods_generator_page_config,
    build_plan_experiments_page_config,
)
from scripts.dashboard.site_render import build_mkdocs_config
from scripts.objective_pool import build_objective_pool_view, pool_schema


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "example_facility"

# Directories a second facility reuses unchanged. Facility-specific images are
# deliberately excluded; _assemble_example_facility reuses only generic asset
# subtrees and generic glyphs.
SHARED_DIRS = ("scripts", "vocab", "schema", "templates")

# Tokens that identify the AIC deployment specifically, as opposed to generic
# microscopy or dashboard terminology.
FACILITY_IDENTITY_TOKENS = ("aic", "turku", "bioscience", "bioimaging", "biocentre")

# Deliberate uses of the `aic` string that are private identifier namespaces
# rather than facility identity. Keep the exceptions narrow: notably,
# "AIC-Turku" must still be detected as a facility identity rather than being
# swallowed by the generic aic-* CSS exception.
PRIVATE_AIC_NAMESPACE = re.compile(
    r"(?i:\[AIC\]|--aic-[A-Za-z0-9_-]+|data-aic-[A-Za-z0-9_-]+|"
    r"\baic-(?!turku\b)[A-Za-z][A-Za-z0-9_-]*|"
    r"\baic\.[A-Za-z][A-Za-z0-9_.-]*)"
    r"|\baic[A-Z][A-Za-z0-9_-]*"
    r"|__aic[A-Z][A-Za-z0-9_-]*"
)

_IDENTITY_TOKEN = re.compile(
    r"\b(" + "|".join(FACILITY_IDENTITY_TOKENS) + r")\b",
    re.IGNORECASE,
)


def _identity_leaks(text: str) -> list[str]:
    """Lines naming the AIC deployment, ignoring only private `aic` namespaces."""
    leaks = []
    for line in text.splitlines():
        if _IDENTITY_TOKEN.search(PRIVATE_AIC_NAMESPACE.sub("", line)):
            leaks.append(line.strip())
    return leaks


class IdentityLeakDetectorTests(unittest.TestCase):
    """The detector the other tests rely on must catch prose and ignore namespaces."""

    def test_facility_prose_is_flagged(self) -> None:
        for line in (
            "check them with AIC staff.",
            "microscopes available at AIC.",
            "Imaging was performed in Turku.",
            "Turku Bioscience Centre",
            "https://github.com/AIC-Turku/AIC-Turku-database",
        ):
            with self.subTest(line=line):
                self.assertEqual(_identity_leaks(line), [line])

    def test_private_namespaces_are_not_flagged(self) -> None:
        for line in (
            '<div class="aic-card__title">',
            "  --aic-status-color: var(--md-default-fg-color--light);",
            "data-aic-charts='{}'",
            '<input id="aicSearch" class="aic-input" type="search" />',
            "window.localStorage.getItem('aic.virtualMicroscope.selectedConfiguration');",
            "console.warn('[AIC] Failed to parse', attrName, e);",
            "window.__aicCharts = [];",
        ):
            with self.subTest(line=line):
                self.assertEqual(_identity_leaks(line), [])


class FacilityShortNameTests(unittest.TestCase):
    """Page copy addressed to visitors resolves one configured name."""

    def test_short_name_is_preferred(self) -> None:
        self.assertEqual(
            facility_short_name({"short_name": "Example Imaging", "full_name": "Long"}),
            "Example Imaging",
        )

    def test_full_name_is_the_fallback(self) -> None:
        self.assertEqual(
            facility_short_name({"full_name": "Example Imaging Facility"}),
            "Example Imaging Facility",
        )

    def test_loader_does_not_mask_full_name_with_default_short_name(self) -> None:
        """Exercise the real facility.yaml merge, not only the resolver in isolation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "facility.yaml").write_text(
                "facility:\n  full_name: Example Imaging Facility\n",
                encoding="utf-8",
            )
            facility = load_facility_config(root)["facility"]
        self.assertEqual(facility_short_name(facility), "Example Imaging Facility")
        self.assertEqual(facility["short_name"], "")

    def test_blank_or_absent_configuration_yields_a_neutral_name(self) -> None:
        for facility in ({}, {"short_name": "   "}, {"short_name": None}):
            with self.subTest(facility=facility):
                self.assertEqual(facility_short_name(facility), DEFAULT_FACILITY_SHORT_NAME)

    def test_default_name_is_not_aic(self) -> None:
        self.assertEqual(_identity_leaks(DEFAULT_FACILITY_SHORT_NAME), [])

    def test_objective_enquiry_uses_full_name_fallback(self) -> None:
        pool = yaml.safe_load(
            (FIXTURE_ROOT / "inventory" / "objective_pool.yaml").read_text(encoding="utf-8")
        )
        view = build_objective_pool_view(
            pool,
            pool_schema(REPO_ROOT),
            {"full_name": "Example Imaging Facility"},
        )
        self.assertTrue(view["items"])
        for item in view["items"]:
            self.assertTrue(item["enquiry"].startswith("Hi Example Imaging Facility team,"))


class TemplateIdentityTests(unittest.TestCase):
    """Templates and browser code must not name a particular facility."""

    def test_page_templates_do_not_hardcode_facility_identity(self) -> None:
        for template in sorted((REPO_ROOT / "scripts" / "templates").iterdir()):
            if not template.is_file():
                continue
            with self.subTest(template=template.name):
                leaks = _identity_leaks(template.read_text(encoding="utf-8"))
                self.assertEqual(
                    leaks,
                    [],
                    f"{template.name} names the AIC deployment; use "
                    f"{{{{ facility_short_name }}}} or facility.yaml instead.",
                )

    def test_browser_code_does_not_hardcode_facility_identity(self) -> None:
        for script in sorted((REPO_ROOT / "assets" / "javascripts").glob("*.js")):
            with self.subTest(script=script.name):
                self.assertEqual(_identity_leaks(script.read_text(encoding="utf-8")), [])

    def test_browser_code_does_not_match_instruments_by_name(self) -> None:
        """Conditional behaviour keys on recorded IDs, never on display names."""
        source = (REPO_ROOT / "assets" / "javascripts" / "methods_generator_app.js").read_text(
            encoding="utf-8"
        )
        for token in ("xcelligence", "rtca esight"):
            self.assertNotIn(token, source.lower())


class MkdocsConfigTests(unittest.TestCase):
    """Site identity in the generated mkdocs.yml comes from configuration."""

    def test_site_name_url_and_branding_follow_configuration(self) -> None:
        config = build_mkdocs_config(
            facility={
                "site_name": "Example Imaging Microscopy Dashboard",
                "public_site_url": "https://example.org/dashboard/",
            },
            branding={
                "logo": "assets/images/example-logo.svg",
                "favicon": "assets/images/example-favicon.svg",
            },
            instruments=[{"id": "scope-example", "display_name": "Example Scope"}],
            retired_instruments=[],
        )

        self.assertEqual(config["site_name"], "Example Imaging Microscopy Dashboard")
        self.assertEqual(config["site_url"], "https://example.org/dashboard/")
        self.assertEqual(config["theme"]["logo"], "assets/images/example-logo.svg")
        self.assertEqual(config["theme"]["favicon"], "assets/images/example-favicon.svg")
        self.assertEqual(_identity_leaks(yaml.safe_dump(config)), [])

    def test_deploy_workflow_does_not_override_configured_site_url(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "deploy-dashboard.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("MKDOCS_SITE_URL", workflow)
        self.assertIn("steps.deployment.outputs.page_url", workflow)


class AcknowledgementConfigTests(unittest.TestCase):
    """Conditional acknowledgements are configuration bound to instrument IDs."""

    def _config(self, acknowledgements: dict, known: set[str] | None = None) -> dict:
        return build_methods_generator_page_config(
            {"acknowledgements": acknowledgements},
            REPO_ROOT / "does-not-exist",
            known,
        )

    def test_additional_entries_are_exported_with_their_instrument_ids(self) -> None:
        config = self._config(
            {
                "standard": "Standard.",
                "additional": [
                    {"text": "Donor credit.", "instrument_ids": ["scope-example"]},
                ],
            },
            {"scope-example"},
        )

        self.assertEqual(
            config["acknowledgements"],
            {
                "standard": "Standard.",
                "additional": [{"text": "Donor credit.", "instrument_ids": ["scope-example"]}],
            },
        )

    def test_absent_additional_is_not_an_error(self) -> None:
        self.assertEqual(self._config({"standard": "Standard."})["acknowledgements"]["additional"], [])

    def test_unknown_instrument_id_fails_the_build(self) -> None:
        with self.assertRaises(AcknowledgementConfigError):
            self._config(
                {"additional": [{"text": "Donor credit.", "instrument_ids": ["scope-gone"]}]},
                {"scope-example"},
            )

    def test_malformed_entries_fail_rather_than_being_dropped(self) -> None:
        for additional in (
            "not-a-list",
            ["not-a-mapping"],
            [{"text": "", "instrument_ids": ["scope-example"]}],
            [{"text": "Donor credit."}],
            [{"text": "Donor credit.", "instrument_ids": []}],
            [{"text": "Donor credit.", "instrument_ids": ["scope-example", 7]}],
        ):
            with self.subTest(additional=additional):
                with self.assertRaises(AcknowledgementConfigError):
                    self._config({"additional": additional})

    def test_legacy_instrument_specific_key_is_rejected_not_ignored(self) -> None:
        """A fork that copied the old key must be told, not silently stripped."""
        with self.assertRaises(AcknowledgementConfigError):
            self._config({"standard": "Standard.", "xcelligence_addition": "Donor credit."})

    def test_production_facility_config_is_valid(self) -> None:
        facility = load_facility_config(REPO_ROOT).get("facility", {})
        instrument_ids = {
            yaml.safe_load(path.read_text(encoding="utf-8"))["instrument"]["instrument_id"]
            for path in (REPO_ROOT / "instruments").rglob("*.yaml")
        }
        config = build_methods_generator_page_config(facility, REPO_ROOT, instrument_ids)
        self.assertTrue(config["acknowledgements"]["standard"])


class PlanExperimentsConfigTests(unittest.TestCase):
    """The assistant prompt names the deploying facility."""

    def test_prompt_config_uses_the_configured_facility(self) -> None:
        config = build_plan_experiments_page_config(
            {"short_name": "Example Imaging", "contact_url": "https://example.org/contact/"}
        )
        self.assertEqual(config["facility_short_name"], "Example Imaging")
        self.assertEqual(config["facility_contact_label"], "Contact Example Imaging Staff")
        self.assertEqual(_identity_leaks(json.dumps(config)), [])


def _assemble_example_facility(root: Path) -> None:
    """Lay out a synthetic deployment: shared code plus the fixture's own data."""
    for name in SHARED_DIRS:
        (root / name).symlink_to(REPO_ROOT / name, target_is_directory=True)

    # Runtime/data assets are reusable; production microscope photos are not.
    assets_root = root / "assets"
    assets_root.mkdir()
    for name in ("javascripts", "stylesheets", "data"):
        source = REPO_ROOT / "assets" / name
        if source.exists():
            (assets_root / name).symlink_to(source, target_is_directory=True)
    images_root = assets_root / "images"
    images_root.mkdir()
    for name in ("logo.svg", "favicon.svg", "placeholder.svg"):
        source = REPO_ROOT / "assets" / "images" / name
        if source.exists():
            (images_root / name).symlink_to(source)

    for name in ("facility.yaml", "instruments", "inventory"):
        source = FIXTURE_ROOT / name
        if source.is_dir():
            shutil.copytree(source, root / name)
        else:
            shutil.copy2(source, root / name)
    (root / "qc" / "sessions").mkdir(parents=True)
    (root / "maintenance" / "events").mkdir(parents=True)


@pytest.fixture(scope="module")
def example_facility_site(tmp_path_factory) -> Path:
    """Build the synthetic facility's complete site with documented commands only."""
    root = tmp_path_factory.mktemp("example_facility")
    _assemble_example_facility(root)
    subprocess.run(
        [sys.executable, "-m", "scripts.dashboard_builder", "--strict"],
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        check=True,
        capture_output=True,
    )
    return root


EXPECTED_PAGES = (
    "index.md",
    "status.md",
    "objective_pool.md",
    "plan_experiments.md",
    "virtual_microscope.md",
    "methods_generator.md",
    "vocabulary_dictionary.md",
    "instruments/scope-example-widefield-one/index.md",
    "instruments/scope-example-confocal/index.md",
    "assets/instruments_data.json",
    "assets/llm_inventory.json",
    "assets/objectives.json",
)


def test_second_facility_builds_every_public_tool(example_facility_site: Path) -> None:
    """Fleet, instruments, objectives, planning, VM and methods all generate."""
    docs = example_facility_site / "dashboard_docs"
    for page in EXPECTED_PAGES:
        assert (docs / page).is_file(), f"{page} was not generated for the second facility"


def test_second_facility_does_not_inherit_production_instrument_photos(
    example_facility_site: Path,
) -> None:
    source_images = example_facility_site / "assets" / "images"
    assert not any(path.name.startswith("scope-") for path in source_images.iterdir())
    for instrument_id in ("scope-example-confocal", "scope-example-widefield-one"):
        page = (
            example_facility_site
            / "dashboard_docs"
            / "instruments"
            / instrument_id
            / "index.md"
        ).read_text(encoding="utf-8")
        assert "placeholder.svg" in page


def test_second_facility_site_never_names_aic(example_facility_site: Path) -> None:
    """No generated page tells an Example Imaging visitor to contact AIC staff."""
    docs = example_facility_site / "dashboard_docs"
    offenders: dict[str, list[str]] = {}
    text_suffixes = {".md", ".html", ".json", ".js", ".css", ".svg", ".yml", ".yaml"}
    for path in sorted(docs.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        leaks = _identity_leaks(path.read_text(encoding="utf-8", errors="replace"))
        if leaks:
            offenders[str(path.relative_to(docs))] = leaks[:3]
    assert offenders == {}


def test_second_facility_pages_address_its_own_name(example_facility_site: Path) -> None:
    docs = example_facility_site / "dashboard_docs"
    for page in ("index.md", "objective_pool.md", "plan_experiments.md", "virtual_microscope.md"):
        assert "Example Imaging" in (docs / page).read_text(encoding="utf-8"), page


def test_second_facility_mkdocs_config_is_generated_from_its_facility_yaml(
    example_facility_site: Path,
) -> None:
    config = yaml.safe_load((example_facility_site / "mkdocs.yml").read_text(encoding="utf-8"))
    assert config["site_name"] == "Example Imaging Microscopy Dashboard"
    assert config["site_url"] == "https://example-imaging.example.org/dashboard/"
    microscopes = next(entry["Microscopes"] for entry in config["nav"] if "Microscopes" in entry)
    assert [label for entry in microscopes for label in entry] == [
        "Example Point-Scanning Confocal",
        "Example Widefield One",
    ]


def test_second_facility_exports_carry_its_own_identity(example_facility_site: Path) -> None:
    """The assistant-ready inventory is grounded in the deploying facility."""
    payload = json.loads(
        (example_facility_site / "dashboard_docs" / "assets" / "llm_inventory.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["facility_name"] == "Example Imaging"
    assert payload["facility_contact_url"] == "https://example.org/imaging/contact/"
    assert payload["public_site_url"] == "https://example-imaging.example.org/dashboard/"
    assert {record["id"] for record in payload["active_microscopes"]} == {
        "scope-example-confocal",
        "scope-example-widefield-one",
    }


def test_second_facility_methods_config_carries_its_acknowledgements(
    example_facility_site: Path,
) -> None:
    page = (example_facility_site / "dashboard_docs" / "methods_generator.md").read_text(
        encoding="utf-8"
    )
    block = page.split('<script id="methods-generator-config" type="application/json">', 1)[1]
    config = json.loads(block.split("</script>", 1)[0].strip())
    acknowledgements = config["acknowledgements"]
    assert "Example Research Infrastructure Programme" in acknowledgements["standard"]
    assert acknowledgements["additional"] == [
        {
            "text": "The confocal was funded by the Example Instrument Donation Fund.",
            "instrument_ids": ["scope-example-confocal"],
        }
    ]


def test_synthetic_facility_stays_out_of_the_production_ledger() -> None:
    """The test facility is a fixture; it must never reach the AIC inventory."""
    production_ids = {
        yaml.safe_load(path.read_text(encoding="utf-8"))["instrument"]["instrument_id"]
        for path in (REPO_ROOT / "instruments").rglob("*.yaml")
    }
    assert not any(identifier.startswith("scope-example") for identifier in production_ids)
    assert not (REPO_ROOT / "instruments" / "Example Widefield One.yaml").exists()
