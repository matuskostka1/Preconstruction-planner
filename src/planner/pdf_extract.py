from __future__ import annotations

import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from .model import Box, DrawingDocument, DrawingPage, TextBlock, to_jsonable

SCALE_RE = re.compile(r"\bM\s*=\s*1\s*:\s*\d+\b", re.IGNORECASE)


def extract_pdf(path: Path) -> DrawingDocument:
    """Extract page size, text boxes, and basic content counts from a PDF."""
    path = Path(path)
    try:
        return _extract_with_pymupdf(path)
    except ModuleNotFoundError:
        return _extract_with_poppler(path)


def save_document_json(document: DrawingDocument, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(to_jsonable(document), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_document_json(path: Path) -> DrawingDocument:
    data = json.loads(path.read_text(encoding="utf-8"))
    pages = []
    for page in data["pages"]:
        blocks = [
            TextBlock(
                text=block["text"],
                box=Box(**block["box"]),
                page_number=block["page_number"],
            )
            for block in page["text_blocks"]
        ]
        pages.append(
            DrawingPage(
                page_number=page["page_number"],
                width=page["width"],
                height=page["height"],
                scale=page.get("scale"),
                text_blocks=blocks,
                vector_path_count=page.get("vector_path_count"),
                image_count=page.get("image_count"),
            )
        )
    return DrawingDocument(source_path=data["source_path"], pages=pages)


def _extract_with_pymupdf(path: Path) -> DrawingDocument:
    import fitz

    pages: list[DrawingPage] = []
    with fitz.open(path) as doc:
        for index, page in enumerate(doc, start=1):
            rect = page.rect
            blocks = []
            for block in page.get_text("blocks"):
                x0, y0, x1, y1, text, *_ = block
                normalized = _clean_text(text)
                if normalized:
                    blocks.append(TextBlock(normalized, Box(x0, y0, x1, y1), index))
            full_text = " ".join(block.text for block in blocks)
            pages.append(
                DrawingPage(
                    page_number=index,
                    width=float(rect.width),
                    height=float(rect.height),
                    scale=_find_scale(full_text),
                    text_blocks=blocks,
                    vector_path_count=len(page.get_drawings()),
                    image_count=len(page.get_images(full=True)),
                )
            )
    return DrawingDocument(source_path=str(path), pages=pages)


def _extract_with_poppler(path: Path) -> DrawingDocument:
    xml = subprocess.run(
        ["pdftohtml", "-xml", "-stdout", str(path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    root = ET.fromstring(xml)
    pages: list[DrawingPage] = []
    for page in root.findall("page"):
        page_number = int(page.attrib["number"])
        blocks = []
        for text_node in page.findall("text"):
            text = _clean_text("".join(text_node.itertext()))
            if not text:
                continue
            left = float(text_node.attrib.get("left", 0))
            top = float(text_node.attrib.get("top", 0))
            width = float(text_node.attrib.get("width", 0))
            height = float(text_node.attrib.get("height", 0))
            blocks.append(
                TextBlock(
                    text=text,
                    box=Box(left, top, left + width, top + height),
                    page_number=page_number,
                )
            )
        full_text = " ".join(block.text for block in blocks)
        pages.append(
            DrawingPage(
                page_number=page_number,
                width=float(page.attrib["width"]),
                height=float(page.attrib["height"]),
                scale=_find_scale(full_text),
                text_blocks=blocks,
            )
        )
    return DrawingDocument(source_path=str(path), pages=pages)


def _find_scale(text: str) -> str | None:
    match = SCALE_RE.search(text)
    if match:
        return re.sub(r"\s+", "", match.group(0)).upper()
    return None


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()

