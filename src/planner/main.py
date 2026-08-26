from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from .layout import generate_layout_pdf, infer_panel_items
from .pdf_extract import extract_pdf, load_document_json, save_document_json
from .report import summarize_items, write_report
from .xlsx_report import read_panel_items, write_panel_csv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="planner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="List PDFs and basic metadata.")
    inspect_parser.add_argument("path", nargs="?", default="technical_drawings")

    extract_parser = subparsers.add_parser("extract", help="Extract one PDF into JSON.")
    extract_parser.add_argument("pdf")
    extract_parser.add_argument("-o", "--output", default="build/extracted.json")

    plan_parser = subparsers.add_parser("plan", help="Generate an annotated layout PDF.")
    plan_parser.add_argument("extracted_json")
    plan_parser.add_argument("-o", "--output", default="build/layout.pdf")

    report_parser = subparsers.add_parser("report", help="Generate CSV/TXT report from JSON or XLSX.")
    report_parser.add_argument("input")
    report_parser.add_argument("-o", "--output-base", default="build/panel_report")

    benchmark_parser = subparsers.add_parser("benchmark", help="Time PDF extraction sequentially and with processes.")
    benchmark_parser.add_argument("path", nargs="?", default="technical_drawings")
    benchmark_parser.add_argument("--workers", type=int, default=2)

    args = parser.parse_args(argv)
    if args.command == "inspect":
        return _inspect(Path(args.path))
    if args.command == "extract":
        return _extract(Path(args.pdf), Path(args.output))
    if args.command == "plan":
        return _plan(Path(args.extracted_json), Path(args.output))
    if args.command == "report":
        return _report(Path(args.input), Path(args.output_base))
    if args.command == "benchmark":
        return _benchmark(Path(args.path), args.workers)
    return 2


def _inspect(path: Path) -> int:
    pdfs = sorted(path.rglob("*.pdf")) if path.is_dir() else [path]
    if not pdfs:
        print(f"No PDFs found under {path}", file=sys.stderr)
        return 1
    for pdf in pdfs:
        try:
            doc = extract_pdf(pdf)
        except Exception as exc:  # pragma: no cover - command-line guard
            print(f"{pdf}: failed: {exc}", file=sys.stderr)
            continue
        page_count = len(doc.pages)
        scales = sorted({page.scale for page in doc.pages if page.scale})
        text_count = sum(len(page.text_blocks) for page in doc.pages)
        images = sum(page.image_count or 0 for page in doc.pages)
        print(f"{pdf}: pages={page_count} text_blocks={text_count} images={images} scales={','.join(scales) or '-'}")
    return 0


def _extract(pdf_path: Path, output_path: Path) -> int:
    document = extract_pdf(pdf_path)
    save_document_json(document, output_path)
    print(json.dumps({"output": str(output_path), "pages": len(document.pages)}, ensure_ascii=False))
    return 0


def _plan(extracted_json: Path, output_path: Path) -> int:
    document = load_document_json(extracted_json)
    items = infer_panel_items(document)
    generate_layout_pdf(document, items, output_path)
    print(json.dumps({"output": str(output_path), **summarize_items(items)}, ensure_ascii=False))
    return 0


def _report(input_path: Path, output_base: Path) -> int:
    if input_path.suffix.lower() == ".xlsx":
        items = read_panel_items(input_path)
    else:
        document = load_document_json(input_path)
        items = infer_panel_items(document)
    csv_path, txt_path = write_report(items, output_base)
    print(json.dumps({"csv": str(csv_path), "summary": str(txt_path), **summarize_items(items)}, ensure_ascii=False))
    return 0


def _benchmark(path: Path, workers: int) -> int:
    pdfs = sorted(path.rglob("*.pdf")) if path.is_dir() else [path]
    started = time.perf_counter()
    sequential = [_extract_summary(pdf) for pdf in pdfs]
    sequential_seconds = time.perf_counter() - started

    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=max(1, workers)) as pool:
        parallel = list(pool.map(_extract_summary, pdfs))
    parallel_seconds = time.perf_counter() - started

    print(
        json.dumps(
            {
                "files": len(pdfs),
                "workers": workers,
                "sequential_seconds": round(sequential_seconds, 3),
                "process_parallel_seconds": round(parallel_seconds, 3),
                "sequential_text_blocks": sum(item["text_blocks"] for item in sequential),
                "parallel_text_blocks": sum(item["text_blocks"] for item in parallel),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _extract_summary(path: Path) -> dict[str, int]:
    document = extract_pdf(path)
    return {"pages": len(document.pages), "text_blocks": sum(len(page.text_blocks) for page in document.pages)}


if __name__ == "__main__":
    raise SystemExit(main())
