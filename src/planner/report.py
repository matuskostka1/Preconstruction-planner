from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .model import PanelItem
from .xlsx_report import write_panel_csv


def summarize_items(items: list[PanelItem]) -> dict[str, float | int]:
    return {
        "panel_rows": len(items),
        "total_count": sum(item.count for item in items),
        "total_area_m2": round(sum(item.area_m2 for item in items), 3),
    }


def write_summary_txt(items: list[PanelItem], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    by_mark: dict[str, dict[str, float | int | str]] = defaultdict(
        lambda: {"mark": "", "count": 0, "area_m2": 0.0}
    )
    for item in items:
        row = by_mark[item.mark]
        row["mark"] = item.mark
        row["count"] = int(row["count"]) + item.count
        row["area_m2"] = round(float(row["area_m2"]) + item.area_m2, 3)

    lines = ["Panel summary", ""]
    for value in summarize_items(items).items():
        lines.append(f"{value[0]}: {value[1]}")
    lines.append("")
    lines.append("By mark:")
    for mark, row in sorted(by_mark.items()):
        lines.append(f"{mark}: {row['count']} ks, {row['area_m2']} m2")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(items: list[PanelItem], output_base: Path) -> tuple[Path, Path]:
    csv_path = output_base.with_suffix(".csv")
    txt_path = output_base.with_suffix(".txt")
    write_panel_csv(items, csv_path)
    write_summary_txt(items, txt_path)
    return csv_path, txt_path

