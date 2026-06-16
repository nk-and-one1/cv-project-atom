"""Deterministic PDF extraction.

pdfplumber is the default — its text-alignment table detection handles
borderless statement tables and keeps multi-line cells together (joined with
``\\n``). camelot is available as a fallback for layouts where pdfplumber's
column detection drifts; it is lazy-imported so the app runs without Ghostscript.
"""

from dataclasses import dataclass, field
from typing import IO

import pdfplumber


@dataclass
class PdfPage:
    index: int
    text: str
    tables: list[list[list[str | None]]] = field(default_factory=list)


def read_pdf(source: IO[bytes], password: str | None = None) -> list[PdfPage]:
    with pdfplumber.open(source, password=password) as pdf:
        return [
            PdfPage(index=i, text=page.extract_text() or "", tables=page.extract_tables())
            for i, page in enumerate(pdf.pages)
        ]


def extract_tables_camelot(path: str, pages: str = "all") -> list[list[list[str]]]:
    """Fallback table extractor. Requires `camelot-py[base]` + Ghostscript."""
    try:
        import camelot
    except ImportError as exc:  # pragma: no cover - optional dep
        raise RuntimeError(
            "camelot is not installed. `pip install 'camelot-py[base]'` and install Ghostscript."
        ) from exc
    for flavor in ("lattice", "stream"):
        tables = camelot.read_pdf(path, pages=pages, flavor=flavor)
        if tables.n:
            return [t.df.values.tolist() for t in tables]
    return []
