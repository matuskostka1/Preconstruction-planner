from pathlib import Path

from planner.xlsx_report import read_panel_items


def test_reads_sample_panel_workbook() -> None:
    path = Path("technical_drawings/Kladací plán/Výpis prvkov - LIND.xlsx")
    items = read_panel_items(path)

    assert len(items) >= 10
    assert any(item.mark == "A1" and item.count == 5 for item in items)
    assert sum(item.count for item in items if item.mark in {"T1", "T2"}) == 94
