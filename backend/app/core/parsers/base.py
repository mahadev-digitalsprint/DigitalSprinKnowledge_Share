from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ParsedPage:
    page: int
    text: str
    bbox: list[float] = field(default_factory=list)  # [x0,y0,x1,y1] optional
    metadata: dict = field(default_factory=dict)


@runtime_checkable
class Parser(Protocol):
    """Common interface for all document parsers."""

    def parse(self, content: bytes, filename: str) -> list[ParsedPage]:
        ...

    @property
    def name(self) -> str:
        ...
