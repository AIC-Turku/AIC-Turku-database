"""Notify IndexNow about the URLs in the deployed sitemap.

The verification key is intentionally a public file: IndexNow verifies that the
site can serve it. For GitHub Pages project sites the key lives under the
project path, so submissions include keyLocation as required by the protocol.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import yaml

ENDPOINT = "https://api.indexnow.org/indexnow"
MAX_URLS = 10_000


def load_site_url(mkdocs_path: Path) -> str:
    config = yaml.safe_load(mkdocs_path.read_text(encoding="utf-8")) or {}
    site_url = str(config.get("site_url") or "").strip()
    if not site_url.startswith(("https://", "http://")):
        raise ValueError("mkdocs.yml must contain an absolute site_url")
    return site_url.rstrip("/") + "/"


def load_sitemap_urls(sitemap_path: Path, site_url: str) -> list[str]:
    root = ET.parse(sitemap_path).getroot()
    urls = []
    sitemap_ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    for loc in root.findall(f"{{{sitemap_ns}}}url/{{{sitemap_ns}}}loc"):
        if not loc.text:
            continue
        url = loc.text.strip()
        if url.startswith(site_url):
            urls.append(url)
    urls = sorted(set(urls))
    if not urls:
        raise ValueError(f"No URLs under {site_url} were found in {sitemap_path}")
    return urls


def build_payload(site_url: str, key: str, key_file_name: str, urls: list[str]) -> dict:
    key_location = urljoin(site_url, key_file_name)
    return {
        "host": urlsplit(site_url).netloc,
        "key": key,
        "keyLocation": key_location,
        "urlList": urls,
    }


def submit(payload: dict) -> int:
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "GitHub-Pages-IndexNow/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
        detail = error.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"IndexNow returned HTTP {status}: {detail}") from error
    if status not in {200, 202}:
        raise RuntimeError(f"Unexpected IndexNow response: HTTP {status}")
    return status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mkdocs", type=Path, default=Path("mkdocs.yml"))
    parser.add_argument("--sitemap", type=Path, default=Path("site/sitemap.xml"))
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    site_url = load_site_url(args.mkdocs)
    key = args.key_file.read_text(encoding="utf-8").strip()
    if not (8 <= len(key) <= 128) or any(ch not in "0123456789abcdefABCDEF-" for ch in key):
        raise SystemExit("IndexNow key must be 8-128 hexadecimal characters or dashes")

    urls = load_sitemap_urls(args.sitemap, site_url)
    statuses = []
    for offset in range(0, len(urls), MAX_URLS):
        batch = urls[offset : offset + MAX_URLS]
        payload = build_payload(site_url, key, args.key_file.name, batch)
        if args.dry_run:
            print(json.dumps(payload, indent=2))
            continue
        statuses.append(submit(payload))

    if args.dry_run:
        print(f"Dry run: {len(urls)} URL(s) would be submitted.")
    else:
        print(f"IndexNow accepted {len(urls)} URL(s); response(s): {statuses}")


if __name__ == "__main__":
    main()
