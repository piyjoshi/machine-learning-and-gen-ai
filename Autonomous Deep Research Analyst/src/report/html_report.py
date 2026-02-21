"""Self-contained HTML report builder."""

from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path

import markdown as md_lib
from pydantic import BaseModel

# ── HTML template ───────────────────────────────────────────────────

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Deep Research Report — {topic}</title>
<style>
  :root {{ --accent: #2563eb; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: "Segoe UI", system-ui, sans-serif; color: #1e293b;
         max-width: 900px; margin: 2rem auto; padding: 0 1.5rem;
         line-height: 1.7; }}
  h1 {{ color: var(--accent); border-bottom: 3px solid var(--accent);
       padding-bottom: .3em; }}
  h2 {{ color: #334155; margin-top: 2em; }}
  h3 {{ color: #475569; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
  th, td {{ border: 1px solid #cbd5e1; padding: .5em .75em; text-align: left; }}
  th {{ background: #f1f5f9; }}
  a {{ color: var(--accent); word-break: break-all; }}
  .cover {{ text-align: center; padding: 4rem 0 2rem; }}
  .cover h1 {{ font-size: 2.2rem; border: none; }}
  .cover .subtitle {{ font-size: 1.3rem; color: #64748b; }}
  .cover .date {{ font-size: .95rem; color: #94a3b8; margin-top: .5rem; }}
  .source-list {{ font-size: .9rem; }}
  .source-list li {{ margin-bottom: .4em; }}
  blockquote {{ border-left: 4px solid var(--accent); margin: 1em 0;
               padding: .5em 1em; background: #f8fafc; }}
  code {{ background: #f1f5f9; padding: .15em .35em; border-radius: 3px;
         font-size: .9em; }}
  img {{ max-width: 100%; }}
  @media print {{
    body {{ max-width: 100%; margin: 0; }}
    .page-break {{ page-break-before: always; }}
  }}
</style>
</head>
<body>

<div class="cover">
  <h1>🔬 Deep Research Report</h1>
  <div class="subtitle">{topic}</div>
  <div class="date">Generated on {date}</div>
</div>

<hr>
<h1>Executive Synthesis</h1>
{synthesis_html}

{sections_html}

<hr class="page-break">
<h1>Sources</h1>
<ol class="source-list">
{sources_html}
</ol>

</body>
</html>
"""


# ── helpers ─────────────────────────────────────────────────────────

def _md_to_html(text: str) -> str:
    """Convert Markdown text to HTML."""
    return md_lib.markdown(text, extensions=["tables", "fenced_code", "nl2br"])


def _img_to_base64(path: Path) -> str:
    """Read a PNG and return an HTML ``<img>`` tag with inline base64 data."""
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode()
    return f'<img src="data:image/png;base64,{b64}" style="max-width:100%;margin:1em 0;">'


def _format_source(src) -> tuple[str, str]:
    """Extract ``(title, url)`` from various source representations."""
    if isinstance(src, dict):
        return src.get("title", "Untitled"), src.get("url", "")
    if isinstance(src, BaseModel):
        return getattr(src, "title", "Untitled"), getattr(src, "url", "")
    return str(src)[:80], str(src)


# ── main builder ────────────────────────────────────────────────────

def build_html_report(
    topic: str,
    results: list[dict],
    synthesis: str,
    chart_paths: dict[str, Path],
    output_path: Path,
) -> None:
    """Assemble a self-contained HTML report and write to *output_path*."""

    synthesis_html = _md_to_html(synthesis)

    sections_parts: list[str] = []
    all_sources: list[tuple[str, str]] = []

    for r in results:
        section_name = r.get("section_name", "Section")
        content = r.get("content", "")
        sources = r.get("sources", [])
        safe = section_name.lower().replace(" ", "_")

        section_html = f'<hr class="page-break">\n<h1>{section_name}</h1>\n'
        section_html += _md_to_html(content)

        chart_path = chart_paths.get(safe)
        if chart_path and chart_path.exists():
            section_html += _img_to_base64(chart_path)

        sections_parts.append(section_html)

        for src in sources or []:
            all_sources.append(_format_source(src))

    # De-duplicate sources
    seen: set[str] = set()
    source_items: list[str] = []
    for title, url in all_sources:
        if url and url not in seen:
            seen.add(url)
            safe_title = title.replace("<", "&lt;").replace(">", "&gt;")
            source_items.append(f'<li><a href="{url}">{safe_title}</a></li>')

    html = HTML_TEMPLATE.format(
        topic=topic,
        date=datetime.now().strftime("%B %d, %Y at %H:%M"),
        synthesis_html=synthesis_html,
        sections_html="\n".join(sections_parts),
        sources_html="\n".join(source_items),
    )

    output_path.write_text(html, encoding="utf-8")
