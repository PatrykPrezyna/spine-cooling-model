"""Convert a README.md (or any Markdown file) to a PDF.

Renders GitHub-style Markdown — headings, tables, lists, code, and local
images — then prints HTML to PDF with Chrome or Edge. Image paths are
resolved relative to the Markdown file, including Windows backslashes
such as ``setup\\image.png``.

Examples::

    python Experiments/readme_to_pdf.py
    python Experiments/readme_to_pdf.py Experiments/20260916_Heat_Capacity_Characterisation_of_the_Catheter
    python Experiments/readme_to_pdf.py --all
"""

from __future__ import annotations

import argparse
import base64
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREATE_NO_WINDOW = 0x08000000

try:
    import markdown
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "The 'markdown' package is required. From the repo venv run:\n"
        "  pip install markdown\n"
        "or:\n"
        "  pip install -r requirements.txt"
    ) from exc


# ![alt](path) — used to turn Windows backslashes into URL-safe slashes.
_MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_SRC_ATTR_RE = re.compile(r"""\bsrc=(["'])([^"']+)\1""", re.IGNORECASE)
_DISPLAY_MATH_RE = re.compile(r"(\$\$.*?\$\$|\\\[.*?\\\])", re.DOTALL)


_CSS = """
@page {
  size: A4;
  margin: 16mm 14mm 18mm 14mm;
}
html, body {
  font-family: "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 10.5pt;
  line-height: 1.45;
  color: #222;
}
h1 { font-size: 20pt; margin: 0 0 0.5em; line-height: 1.2; }
h2 {
  font-size: 13.5pt;
  margin: 1.4em 0 0.45em;
  padding-bottom: 0.15em;
  border-bottom: 1px solid #d0d0d0;
}
h3 { font-size: 11.5pt; margin: 1.1em 0 0.35em; }
p { margin: 0.55em 0; }
ul, ol { margin: 0.4em 0 0.6em 1.3em; }
li { margin: 0.2em 0; }
table {
  border-collapse: collapse;
  width: 100%;
  margin: 0.9em 0;
  font-size: 9pt;
  page-break-inside: avoid;
}
th, td {
  border: 1px solid #c8c8c8;
  padding: 4px 7px;
  text-align: left;
  vertical-align: middle;
}
th { background: #f3f3f3; font-weight: 600; }
img {
  max-width: 100%;
  max-height: 210mm;
  height: auto;
  display: block;
  margin: 0.7em auto;
  page-break-inside: avoid;
}
td img {
  margin: 0.15em auto;
  max-height: 85mm;
}
pre, code { font-family: Consolas, "Courier New", monospace; font-size: 8.8pt; }
code {
  background: #f4f5f7;
  padding: 0.05em 0.28em;
  border-radius: 3px;
}
pre {
  background: #f6f8fa;
  padding: 10px 12px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid #e6e8eb;
  border-radius: 4px;
}
pre code { background: none; padding: 0; }
blockquote {
  margin: 0.6em 0;
  padding: 0.1em 0 0.1em 0.9em;
  border-left: 3px solid #cfcfcf;
  color: #444;
}
a { color: #1a54c2; text-decoration: none; }
.missing-image {
  border: 1px dashed #c00;
  color: #a00;
  padding: 8px 10px;
  font-size: 9pt;
  margin: 0.6em 0;
}
.math {
  display: block;
  text-align: center;
  margin: 0.8em 0;
  white-space: pre-wrap;
  font-family: Consolas, "Courier New", monospace;
  font-size: 9.5pt;
}
"""


def _normalize_image_paths(markdown_text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        alt, src = match.group(1), match.group(2).strip()
        src = src.replace("\\", "/")
        return f"![{alt}]({src})"

    return _MD_IMAGE_RE.sub(repl, markdown_text)


def _protect_display_math(markdown_text: str) -> tuple[str, list[str]]:
    """Keep \\[ \\] / $$ blocks from being eaten by Markdown escaping."""
    blocks: list[str] = []

    def repl(match: re.Match[str]) -> str:
        blocks.append(match.group(0).strip())
        return f"\n\n@@MATH{len(blocks) - 1}@@\n\n"

    return _DISPLAY_MATH_RE.sub(repl, markdown_text), blocks


def _restore_display_math(html: str, blocks: list[str]) -> str:
    for index, block in enumerate(blocks):
        inner = block
        if inner.startswith("$$") and inner.endswith("$$"):
            inner = inner[2:-2].strip()
        elif inner.startswith("\\[") and inner.endswith("\\]"):
            inner = inner[2:-2].strip()
        html = html.replace(
            f"<p>@@MATH{index}@@</p>",
            f'<div class="math">{_escape_html(inner)}</div>',
        )
        html = html.replace(f"@@MATH{index}@@", _escape_html(inner))
    return html


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _title_from_markdown(markdown_text: str, fallback: str) -> str:
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def _file_to_data_uri(path: Path) -> str | None:
    if not path.is_file():
        return None
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def embed_local_images(html: str, base_dir: Path) -> str:
    """Replace relative <img src> with base64 data URIs so print-to-PDF works."""

    def repl(match: re.Match[str]) -> str:
        tag = match.group(0)
        src_match = _SRC_ATTR_RE.search(tag)
        if src_match is None:
            return tag
        src = src_match.group(2)
        if src.startswith(("data:", "http://", "https://")):
            return tag
        raw = src.replace("\\", "/").split("?")[0].split("#")[0]
        path = (base_dir / raw).resolve()
        uri = _file_to_data_uri(path)
        if uri is None:
            return (
                f'<div class="missing-image">Missing image: '
                f"{_escape_html(path.name)}</div>"
            )
        return _SRC_ATTR_RE.sub(
            lambda m: f"src={m.group(1)}{uri}{m.group(1)}",
            tag,
            count=1,
        )

    return _IMG_TAG_RE.sub(repl, html)


def markdown_to_html(markdown_path: Path) -> str:
    text = markdown_path.read_text(encoding="utf-8")
    title = _title_from_markdown(text, markdown_path.stem)
    text = _normalize_image_paths(text)
    text, math_blocks = _protect_display_math(text)
    body = markdown.markdown(
        text,
        extensions=["extra", "sane_lists", "smarty"],
        output_format="html5",
    )
    body = _restore_display_math(body, math_blocks)
    body = embed_local_images(body, markdown_path.parent)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>{_escape_html(title)}</title>\n"
        f"<style>{_CSS}</style>\n"
        "</head>\n"
        f"<body>\n{body}\n</body>\n"
        "</html>\n"
    )


def find_chromium() -> Path:
    named = [
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("msedge"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    program_files = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
    program_files_x86 = Path(
        os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    )
    candidates = [Path(p) for p in named if p]
    candidates.extend(
        [
            program_files / "Google/Chrome/Application/chrome.exe",
            program_files_x86 / "Microsoft/Edge/Application/msedge.exe",
            program_files / "Microsoft/Edge/Application/msedge.exe",
            Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe",
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/usr/bin/google-chrome"),
            Path("/usr/bin/chromium-browser"),
            Path("/usr/bin/chromium"),
        ]
    )
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(
        "Chrome or Edge was not found. Install Google Chrome (or Microsoft Edge) "
        "so this script can print HTML to PDF."
    )


def html_to_pdf(html: str, pdf_path: Path) -> None:
    browser = find_chromium()
    pdf_path = pdf_path.resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists():
        pdf_path.unlink()

    with tempfile.TemporaryDirectory(prefix="readme_to_pdf_") as tmp:
        tmp_dir = Path(tmp)
        html_path = tmp_dir / "readme.html"
        html_path.write_text(html, encoding="utf-8")
        profile_dir = tmp_dir / "chrome-profile"
        profile_dir.mkdir()
        cmd = [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--disable-extensions",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={profile_dir}",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            html_path.resolve().as_uri(),
        ]
        kwargs: dict = {
            "check": False,
            "capture_output": True,
            "text": True,
            "timeout": 120,
        }
        if os.name == "nt":
            kwargs["creationflags"] = CREATE_NO_WINDOW
        result = subprocess.run(cmd, **kwargs)
        if result.returncode != 0 or not pdf_path.is_file() or pdf_path.stat().st_size == 0:
            # Older Chrome builds only accept --headless (not --headless=new).
            cmd[1] = "--headless"
            result = subprocess.run(cmd, **kwargs)
        if not pdf_path.is_file() or pdf_path.stat().st_size == 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(
                f"PDF was not written to {pdf_path}"
                + (f"\n{detail}" if detail else "")
            )


def resolve_markdown_path(raw: str | Path) -> Path:
    path = Path(raw)
    if path.is_dir():
        candidate = path / "README.md"
        if not candidate.is_file():
            raise FileNotFoundError(f"No README.md in {path.resolve()}")
        return candidate
    if path.is_file():
        return path
    raise FileNotFoundError(f"Markdown file not found: {path}")


def default_pdf_path(markdown_path: Path) -> Path:
    return markdown_path.with_suffix(".pdf")


def convert_file(markdown_path: Path, pdf_path: Path | None = None) -> Path:
    markdown_path = resolve_markdown_path(markdown_path)
    pdf_path = pdf_path or default_pdf_path(markdown_path)
    html = markdown_to_html(markdown_path)
    html_to_pdf(html, pdf_path)
    return pdf_path


def experiment_readmes() -> list[Path]:
    found: list[Path] = []
    for folder in sorted((ROOT / "Experiments").iterdir()):
        if not folder.is_dir():
            continue
        readme = folder / "README.md"
        if readme.is_file():
            found.append(readme)
    return found


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert README.md (or any Markdown file) to PDF."
    )
    parser.add_argument(
        "markdown",
        nargs="?",
        default="README.md",
        help="Markdown file, or a folder that contains README.md (default: ./README.md)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output PDF path (ignored with --all)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Convert every Experiments/*/README.md",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.all:
        readmes = experiment_readmes()
        if not readmes:
            print("No Experiments/*/README.md files found.", file=sys.stderr)
            return 1
        failures = 0
        for readme in readmes:
            try:
                pdf_path = convert_file(readme)
                print(f"Wrote {pdf_path}")
            except Exception as exc:  # noqa: BLE001 — keep converting the rest
                failures += 1
                print(f"Failed {readme}: {exc}", file=sys.stderr)
        return 1 if failures else 0

    pdf_path = convert_file(args.markdown, args.output)
    print(f"Wrote {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
