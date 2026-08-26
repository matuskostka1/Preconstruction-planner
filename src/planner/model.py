from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Box:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass(frozen=True)
class TextBlock:
    text: str
    box: Box
    page_number: int


@dataclass(frozen=True)
class DrawingPage:
    page_number: int
    width: float
    height: float
    scale: str | None = None
    text_blocks: list[TextBlock] = field(default_factory=list)
    vector_path_count: int | None = None
    image_count: int | None = None


@dataclass(frozen=True)
class DrawingDocument:
    source_path: str
    pages: list[DrawingPage]


@dataclass(frozen=True)
class PanelItem:
    view: str
    mark: str
    length_m: float
    width_m: float
    count: int
    area_m2: float
    note: str = ""


def to_jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value

