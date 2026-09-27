import json
from pathlib import Path

from scripts.dashboard.site_render import build_mkdocs_config


ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif", ".avif"}


def test_generated_image_rights_cover_every_public_image(generated_dashboard):
    payload = json.loads(
        (generated_dashboard / "assets" / "image_rights.json").read_text(encoding="utf-8")
    )
    published = {
        row["path"]
        for row in payload["images"]
        if isinstance(row, dict) and row.get("path")
    }
    expected = {
        f"assets/images/{path.relative_to(ROOT / 'assets' / 'images').as_posix()}"
        for path in (ROOT / "assets" / "images").rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    }
    assert published == expected
    assert all(row["rights_status"] == "copyrighted" for row in payload["images"])
    assert all(row["reuse"] == "permission_required" for row in payload["images"])
    assert all(row["copyright_notice"] for row in payload["images"])


def test_generated_discovery_files_exist(generated_dashboard):
    assert (generated_dashboard / "llms.txt").is_file()
    assert (generated_dashboard / "licensing.md").is_file()
    inventory = json.loads(
        (generated_dashboard / "assets" / "llm_inventory.json").read_text(encoding="utf-8")
    )
    assert inventory["metadata"]["code_license"] == "MIT"
    assert inventory["metadata"]["image_reuse_policy"] == "copyrighted_permission_required"


def test_mkdocs_uses_discovery_override():
    config = build_mkdocs_config(
        facility={
            "site_name": "Example",
            "public_site_url": "https://example.org/site/",
            "source_repository_url": "https://github.com/example/site",
        },
        branding={},
        instruments=[],
        retired_instruments=[],
    )
    assert config["theme"]["custom_dir"] == "overrides"
