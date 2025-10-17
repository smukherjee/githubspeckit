"""Generate static HTML documentation (ReDoc) for the combined OpenAPI spec.

Usage:
  python scripts/generate_openapi_html.py \
      --spec specs/001-modern-enterprise-grade/contracts/openapi-combined.yaml \
      --out docs/api/index.html

Requires: pyyaml installed (already present for bundling).
No external network calls; embeds the spec JSON into a ReDoc HTML shell.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import yaml
from script_logger import get_logger

logger = get_logger("generate_openapi_html")

REDOC_CDN = "https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--spec", required=True, type=Path, help="Path to combined OpenAPI YAML")
    p.add_argument("--out", required=True, type=Path, help="Output HTML file path")
    return p.parse_args()


def build_html(spec: dict) -> str:
    # Convert spec to JSON string (ensure ASCII safe escaping is off for readability)
    spec_json = json.dumps(spec, ensure_ascii=False)
    title = spec.get('info', {}).get('title', 'API Docs')
    # Use str.format to avoid accidental brace interpolation in JS object
    template = (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"UTF-8\" />\n"
        "  <title>{title}</title>\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>\n"
        "  <style>body {{ margin:0; padding:0; }}</style>\n"
        "</head>\n"
        "<body>\n"
        "  <redoc></redoc>\n"
        "  <script>\n"
        "    const spec = {spec_json};\n"
        "    window.addEventListener('load', function() {{\n"
        "      Redoc.init(spec, {{\n"
        "        hideDownloadButton: false,\n"
        "        expandResponses: '200,400'\n"
        "      }}, document.querySelector('redoc'));\n"
        "    }});\n"
        "  </script>\n"
        "  <script src=\"{redoc_cdn}\"></script>\n"
        "</body>\n"
        "</html>"
    )
    return template.format(title=title, spec_json=spec_json, redoc_cdn=REDOC_CDN)


def main():
    args = parse_args()
    if not args.spec.exists():
        raise SystemExit(f"Spec not found: {args.spec}")
    data = yaml.safe_load(args.spec.read_text(encoding="utf-8")) or {}
    html = build_html(data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    logger.success("html_generated", output_path=str(args.out), spec_path=str(args.spec))

if __name__ == "__main__":  # pragma: no cover
    main()
