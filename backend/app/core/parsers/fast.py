from __future__ import annotations

import io
import logging
import re
import zipfile
from xml.etree import ElementTree

from pypdf import PdfReader

from app.core.parsers.base import ParsedPage

logger = logging.getLogger(__name__)

SUPPORTED = {"pdf", "txt", "md", "rst", "docx", "pptx", "xlsx"}


class FastParser:
    @property
    def name(self) -> str:
        return "fast"

    def parse(self, content: bytes, filename: str) -> list[ParsedPage]:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext not in SUPPORTED:
            raise ValueError(f"FastParser does not support .{ext} files")

        if ext == "pdf":
            return self._parse_pdf(content, filename)
        if ext in {"txt", "md", "rst"}:
            return self._parse_text(content)
        if ext == "docx":
            return self._parse_docx(content)
        if ext == "pptx":
            return self._parse_pptx(content)
        if ext == "xlsx":
            return self._parse_xlsx(content)
        raise ValueError(f"Unhandled extension: .{ext}")

    def _parse_pdf(self, content: bytes, filename: str) -> list[ParsedPage]:
        reader = PdfReader(io.BytesIO(content))
        pages: list[ParsedPage] = []
        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                logger.warning("pypdf failed on page %d of %s: %s", i + 1, filename, exc)
                text = ""
            pages.append(ParsedPage(page=i + 1, text=text.strip()))
        return pages

    def _parse_text(self, content: bytes) -> list[ParsedPage]:
        text = content.decode("utf-8", errors="replace")
        return [ParsedPage(page=1, text=text)]

    def _parse_docx(self, content: bytes) -> list[ParsedPage]:
        text = self._extract_office_xml_text(content, ["word/document.xml"])
        return [ParsedPage(page=1, text=text)]

    def _parse_pptx(self, content: bytes) -> list[ParsedPage]:
        pages: list[ParsedPage] = []
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            slide_names = sorted(
                name
                for name in archive.namelist()
                if name.startswith("ppt/slides/slide") and name.endswith(".xml")
            )
            for index, slide_name in enumerate(slide_names, start=1):
                text = self._xml_to_text(archive.read(slide_name))
                pages.append(ParsedPage(page=index, text=text))
        return pages or [ParsedPage(page=1, text="")]

    def _parse_xlsx(self, content: bytes) -> list[ParsedPage]:
        pages: list[ParsedPage] = []
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            shared_strings = self._load_shared_strings(archive)
            sheet_names = sorted(
                name
                for name in archive.namelist()
                if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
            )
            for index, sheet_name in enumerate(sheet_names, start=1):
                xml = archive.read(sheet_name)
                text = self._worksheet_to_text(xml, shared_strings)
                pages.append(ParsedPage(page=index, text=text))
        return pages or [ParsedPage(page=1, text="")]

    def _extract_office_xml_text(self, content: bytes, members: list[str]) -> str:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            parts = []
            for member in members:
                if member not in archive.namelist():
                    continue
                parts.append(self._xml_to_text(archive.read(member)))
            return "\n\n".join(part for part in parts if part).strip()

    def _xml_to_text(self, xml_bytes: bytes) -> str:
        root = ElementTree.fromstring(xml_bytes)
        texts = [node.text.strip() for node in root.iter() if node.text and node.text.strip()]
        return "\n".join(texts)

    def _load_shared_strings(self, archive: zipfile.ZipFile) -> list[str]:
        name = "xl/sharedStrings.xml"
        if name not in archive.namelist():
            return []
        root = ElementTree.fromstring(archive.read(name))
        return [node.text or "" for node in root.iter() if node.tag.endswith("}t") or node.tag == "t"]

    def _worksheet_to_text(self, xml_bytes: bytes, shared_strings: list[str]) -> str:
        root = ElementTree.fromstring(xml_bytes)
        rows: list[str] = []
        for row in root.iter():
            if not (row.tag.endswith("}row") or row.tag == "row"):
                continue

            cells: list[str] = []
            for cell in row:
                if not (cell.tag.endswith("}c") or cell.tag == "c"):
                    continue
                cell_type = cell.attrib.get("t")
                value = ""
                for child in cell:
                    if child.tag.endswith("}v") or child.tag == "v":
                        value = child.text or ""
                    elif child.tag.endswith("}is") or child.tag == "is":
                        value = self._xml_to_text(ElementTree.tostring(child, encoding="utf-8"))
                if cell_type == "s" and value.isdigit():
                    index = int(value)
                    value = shared_strings[index] if index < len(shared_strings) else value
                if value:
                    cells.append(re.sub(r"\s+", " ", value).strip())
            if cells:
                rows.append(" | ".join(cells))
        return "\n".join(rows)
