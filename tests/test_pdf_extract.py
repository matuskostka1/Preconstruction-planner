from pathlib import Path

from planner.pdf_extract import extract_pdf


def test_extracts_text_from_archicad_pdf() -> None:
    document = extract_pdf(Path("technical_drawings/001 N01 1250X420.pdf"))

    assert len(document.pages) == 1
    assert document.pages[0].scale == "M=1:50"
    all_text = " ".join(block.text for block in document.pages[0].text_blocks)
    assert "PÔDORYS" in all_text
    assert "O1" in all_text
