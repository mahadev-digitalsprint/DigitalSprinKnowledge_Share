from __future__ import annotations

from dataclasses import dataclass

from app.core.parsers.base import ParsedPage, Parser
from app.core.parsers.cold_stub import ColdParser
from app.core.parsers.fast import FastParser
from app.core.registry import load_registry


@dataclass
class ParseHeuristics:
    ext: str
    pages: int
    total_chars: int
    avg_chars_per_page: float
    table_density: float
    is_scanned: bool
    high_accuracy: bool = False


class LiteParseAdapter:
    def __init__(self) -> None:
        self._delegate = FastParser()

    @property
    def name(self) -> str:
        return "fast"

    def parse(self, content: bytes, filename: str) -> list[ParsedPage]:
        return self._delegate.parse(content, filename)


class LlamaParseAdapter:
    def __init__(self, name: str, ocr: bool = False) -> None:
        self._delegate = ColdParser()
        self._name = name
        self._ocr = ocr

    @property
    def name(self) -> str:
        return self._name

    def parse(self, content: bytes, filename: str) -> list[ParsedPage]:
        return self._delegate.parse(content, filename)


class FastFallbackAdapter:
    def __init__(self, name: str) -> None:
        self._delegate = FastParser()
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def parse(self, content: bytes, filename: str) -> list[ParsedPage]:
        return self._delegate.parse(content, filename)


def build_parser_registry() -> dict[str, Parser]:
    return {
        "fast": LiteParseAdapter(),
        "premium": LlamaParseAdapter(name="premium"),
        "ocr": LlamaParseAdapter(name="ocr", ocr=True),
        "marker": FastFallbackAdapter(name="marker"),
        "unstructured": FastFallbackAdapter(name="unstructured"),
    }


def analyze_pages(
    pages: list[ParsedPage],
    filename: str,
    *,
    high_accuracy: bool = False,
) -> ParseHeuristics:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    total_chars = sum(len(page.text) for page in pages)
    avg_chars_per_page = total_chars / max(len(pages), 1)

    total_lines = 0
    table_like_lines = 0
    for page in pages:
        lines = [line for line in page.text.splitlines() if line.strip()]
        total_lines += len(lines)
        table_like_lines += sum(
            1
            for line in lines
            if "|" in line or "\t" in line or line.count("  ") >= 4
        )

    table_density = table_like_lines / max(total_lines, 1)
    is_scanned = ext == "pdf" and avg_chars_per_page < 80

    return ParseHeuristics(
        ext=ext,
        pages=len(pages),
        total_chars=total_chars,
        avg_chars_per_page=avg_chars_per_page,
        table_density=table_density,
        is_scanned=is_scanned,
        high_accuracy=high_accuracy,
    )


def get_parser(name: str) -> Parser:
    registry = build_parser_registry()
    parser = registry.get(name)
    if parser is None:
        raise KeyError(f"Unknown parser '{name}'")
    return parser


def pick_hot_parser() -> Parser:
    parser_name = load_registry().parsers.hot
    return get_parser(parser_name)


def pick_cold_parser(heuristics: ParseHeuristics) -> Parser | None:
    registry = load_registry()
    parser_name = ""

    if heuristics.high_accuracy:
        parser_name = registry.parsers.cold_default
    elif heuristics.is_scanned:
        parser_name = registry.parsers.cold_scanned
    elif heuristics.ext in {"pptx", "xlsx", "docx"}:
        parser_name = registry.parsers.cold_default
    elif heuristics.table_density > 0.15:
        parser_name = registry.parsers.cold_default
    elif heuristics.pages > 50:
        parser_name = registry.parsers.cold_default

    if not parser_name or parser_name in {"fast", registry.parsers.hot}:
        return None

    return get_parser(parser_name)
