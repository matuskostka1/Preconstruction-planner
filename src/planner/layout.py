from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .model import DrawingDocument, PanelItem

PANEL_MARK_RE = re.compile(r"\b[A-Z][0-9]+\b")


def infer_panel_items(document: DrawingDocument, default_width_m: float = 1.0) -> list[PanelItem]:
    """Infer a rough panel list from visible panel marks.

    This is intentionally conservative: it counts labels visible in generated
    drawings and assigns placeholder lengths until geometry calibration is added.
    """
    counter: Counter[tuple[str, str]] = Counter()
    for page in document.pages:
        view = _infer_view_name(page.text_blocks)
        for block in page.text_blocks:
            for mark in PANEL_MARK_RE.findall(block.text):
                if mark.startswith(("D", "O")):
                    continue
                counter[(view, mark)] += 1

    items = []
    for (view, mark), count in sorted(counter.items()):
        items.append(
            PanelItem(
                view=view,
                mark=mark,
                length_m=0.0,
                width_m=default_width_m,
                count=count,
                area_m2=0.0,
                note="length pending geometry calibration",
            )
        )
    return items


def generate_layout_pdf(document: DrawingDocument, items: list[PanelItem], output_path: Path) -> None:
    """Generate a simple visual audit PDF from extracted panel marks."""
    try:
        _generate_with_pymupdf(document, items, output_path)
    except ModuleNotFoundError:
        _generate_minimal_pdf(document, items, output_path)


def _generate_with_pymupdf(document: DrawingDocument, items: list[PanelItem], output_path: Path) -> None:
    import fitz

    output_path.parent.mkdir(parents=True, exist_ok=True)
    source = fitz.open(document.source_path)
    out = fitz.open()
    mark_counts = Counter(item.mark for item in items)

    for page_index, source_page in enumerate(source):
        page = out.new_page(width=source_page.rect.width, height=source_page.rect.height)
        page.show_pdf_page(page.rect, source, page_index)
        extracted_page = document.pages[page_index]
        for block in extracted_page.text_blocks:
            if PANEL_MARK_RE.fullmatch(block.text) and not block.text.startswith(("D", "O")):
                rect = fitz.Rect(block.box.x0, block.box.y0, block.box.x1, block.box.y1)
                page.draw_rect(rect + (-2, -2, 2, 2), color=(1, 0, 0), width=0.8)

        _draw_summary(page, mark_counts)

    source.close()
    out.save(output_path)
    out.close()


def _draw_summary(page: object, mark_counts: Counter[str]) -> None:
    import fitz

    left = 36
    top = page.rect.height - 120
    width = 260
    height = 84
    rect = fitz.Rect(left, top, left + width, top + height)
    page.draw_rect(rect, color=(0, 0, 0), fill=(1, 1, 1), width=0.8)
    lines = ["Detected panel marks"]
    if mark_counts:
        lines.extend(f"{mark}: {count} ks" for mark, count in sorted(mark_counts.items())[:8])
    else:
        lines.append("No panel marks detected")
    page.insert_textbox(rect + (8, 8, -8, -8), "\n".join(lines), fontsize=8, color=(0, 0, 0))


def _generate_minimal_pdf(document: DrawingDocument, items: list[PanelItem], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "Planner - prototype layout summary",
        f"Source: {document.source_path}",
        f"Pages: {len(document.pages)}",
        "",
        "Detected panel marks:",
    ]
    counts = Counter(item.mark for item in items)
    if counts:
        lines.extend(f"{mark}: {count} ks" for mark, count in sorted(counts.items()))
    else:
        lines.append("No panel marks detected")
    _write_basic_pdf(output_path, lines)


def _write_basic_pdf(path: Path, lines: list[str]) -> None:
    escaped_lines = [_escape_pdf_text(line) for line in lines]
    text_ops = ["BT", "/F1 10 Tf", "50 790 Td"]
    for index, line in enumerate(escaped_lines):
        if index:
            text_ops.append("0 -14 Td")
        text_ops.append(f"({line}) Tj")
    text_ops.append("ET")
    stream = "\n".join(text_ops).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{number} 0 obj\n".encode("ascii"))
        content.extend(obj)
        content.extend(b"\nendobj\n")
    xref = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    content.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    content.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(content)


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _infer_view_name(blocks: object) -> str:
    for block in blocks:
        text = block.text.upper()
        if "POHĽAD" in text or "POHLAD" in text:
            return block.text
    return "Unknown"
