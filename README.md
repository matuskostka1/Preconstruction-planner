# Preconstruction planner

CLI prototype for generating a `kladací plán` and panel takeoff from CAD vector PDF technical drawings.

## CLI commands

```bash
python -m planner.main inspect technical_drawings
python -m planner.main extract "technical_drawings/Kladací plán/Kladací plán - fasáda.pdf" -o build/fasada.json
python -m planner.main plan build/fasada.json -o build/fasada-layout.pdf
python -m planner.main report "technical_drawings/Kladací plán/Výpis prvkov - LIND.xlsx" -o build/vypis-prvkov
python -m planner.main benchmark technical_drawings --workers 4
```

The app prefers PyMuPDF for PDF work. If PyMuPDF is unavailable, extraction falls back to the system `pdftohtml` command from Poppler and layout generation writes a basic summary PDF instead of an annotated drawing overlay.

## Container

Python 3.14:

```bash
podman build -t planner .
podman run --rm -v "$PWD:/work:Z" -w /work planner inspect technical_drawings
```

Python 3.14t (without GIL):

```bash
podman build --build-arg PYTHON_FLAVOR=freethreaded -t planner:free-threaded .
podman run --rm -v "$PWD:/work:Z" -w /work planner:free-threaded inspect technical_drawings
```

## Notes

The current layout generator is intentionally an audit/prototype output: it highlights detected panel marks and writes summary counts. Real panel lengths, cutting logic, and price calculation should be added after geometry calibration is stable.
