"""Add primary page images to the XML sitemap for image discovery."""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin

import yaml

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
IMAGE_NS = "http://www.google.com/schemas/sitemap-image/1.1"
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".avif")


def load_site_url(mkdocs_path: Path) -> str:
    config = yaml.safe_load(mkdocs_path.read_text(encoding="utf-8")) or {}
    site_url = str(config.get("site_url") or "").strip()
    if not site_url.startswith(("https://", "http://")):
        raise ValueError("mkdocs.yml must contain an absolute site_url")
    return site_url.rstrip("/") + "/"


def primary_image(site_root: Path, relative_page: str) -> Path | None:
    parts = [part for part in relative_page.strip("/").split("/") if part]
    if len(parts) != 2 or parts[0] not in {"instruments", "supervisors"}:
        return None
    slug = parts[1]
    roots = [
        site_root / "assets" / "images",
        site_root / "assets" / "images" / "supervisors",
    ]
    for root in roots:
        for suffix in IMAGE_SUFFIXES:
            candidate = root / f"{slug}{suffix}"
            if candidate.is_file():
                return candidate
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mkdocs", type=Path, default=Path("mkdocs.yml"))
    parser.add_argument("--site", type=Path, default=Path("site"))
    args = parser.parse_args()

    site_url = load_site_url(args.mkdocs)
    sitemap_path = args.site / "sitemap.xml"
    tree = ET.parse(sitemap_path)
    root = tree.getroot()

    ET.register_namespace("", SITEMAP_NS)
    ET.register_namespace("image", IMAGE_NS)

    added = 0
    for url_node in root.findall(f"{{{SITEMAP_NS}}}url"):
        loc_node = url_node.find(f"{{{SITEMAP_NS}}}loc")
        if loc_node is None or not loc_node.text:
            continue
        page_url = loc_node.text.strip()
        if not page_url.startswith(site_url):
            continue
        if url_node.find(f"{{{IMAGE_NS}}}image") is not None:
            continue
        relative_page = page_url[len(site_url):]
        image_path = primary_image(args.site, relative_page)
        if image_path is None:
            continue
        image_rel = image_path.relative_to(args.site).as_posix()
        image_node = ET.SubElement(url_node, f"{{{IMAGE_NS}}}image")
        image_loc = ET.SubElement(image_node, f"{{{IMAGE_NS}}}loc")
        image_loc.text = urljoin(site_url, image_rel)
        added += 1

    tree.write(sitemap_path, encoding="utf-8", xml_declaration=True)
    print(f"Added {added} primary image(s) to {sitemap_path}.")


if __name__ == "__main__":
    main()
