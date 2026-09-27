import json
from pathlib import Path

from PIL import Image

from scripts.dashboard.site_render import build_mkdocs_config
from scripts.submit_indexnow import load_sitemap_urls


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
    assert (generated_dashboard / "9f4a2c7e16b8d0e3c5a7f9b1d2e4c6a8.txt").is_file()
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



def test_instrument_pages_expose_breadcrumbs_and_social_images(generated_dashboard):
    page = (
        generated_dashboard
        / "instruments"
        / "scope-nikon-crest-v3"
        / "index.md"
    ).read_text(encoding="utf-8")
    assert "BreadcrumbList" in page
    assert 'image: "https://aic-turku.github.io/AIC-Turku-database/assets/images/scope-nikon-crest-v3.jpg"' in page


def test_indexnow_ignores_image_sitemap_locations(tmp_path):
    sitemap = tmp_path / "sitemap.xml"
    sitemap.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  <url>
    <loc>https://example.org/site/page/</loc>
    <image:image><image:loc>https://example.org/site/image.jpg</image:loc></image:image>
  </url>
</urlset>
""",
        encoding="utf-8",
    )
    assert load_sitemap_urls(sitemap, "https://example.org/site/") == [
        "https://example.org/site/page/"
    ]



def test_deployed_microscope_jpegs_are_web_sized(generated_dashboard):
    source_images = ROOT / "assets" / "images"
    public_images = generated_dashboard / "assets" / "images"
    deployed = sorted(public_images.glob("scope-*.jpg"))
    assert deployed
    for path in deployed:
        with Image.open(path) as image:
            assert max(image.size) <= 1600, path.name

    large_source = source_images / "scope-olympus-bx60.jpg"
    large_public = public_images / "scope-olympus-bx60.jpg"
    assert large_public.stat().st_size < large_source.stat().st_size
