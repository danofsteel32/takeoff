import hashlib
import logging
from pathlib import Path

import pymupdf as fitz  # type: ignore[import-untyped]
from attrs import define

DPI = 150

logger = logging.getLogger(__name__)


@define
class BBox:
    x0: float
    y0: float
    x1: float
    y1: float


@define
class TextBlock:
    text: str
    bbox: BBox


@define
class ProcessedPage:
    page_number: int
    width: int
    height: int
    zoom_factor: float
    raw_text: str
    page_image: fitz.Pixmap
    text_blocks: list[TextBlock]


@define
class ProcessedPDF:
    filename: str
    sha256sum: str
    pages: list[ProcessedPage]


def get_sha256sum(path: Path, chunk_size: int = 65536) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def process(path: Path) -> ProcessedPDF:
    logger.debug("Begin processing %s ...", path.name)

    doc = fitz.open(path)

    logger.debug("Found %d pages in %s", doc.page_count, doc.name)

    pages = []

    for n in range(doc.page_count):
        page_num = n + 1

        logger.debug("Processing page %d/%d in %s", page_num, doc.page_count, doc.name)
        page = doc[n]

        logger.debug("Extracting text")
        raw_text = page.get_text("text")
        logger.debug(
            "Extracted %d chars from page %d in %s", len(raw_text), page_num, doc.name
        )

        logger.debug("Extracting text blocks")
        dict_data = page.get_text("dict")
        blocks = dict_data.get("blocks", [])
        logger.debug("Found %d blocks", len(blocks))

        text_blocks = []
        # blocks -> lines -> spans
        for block in blocks:
            # Block type 0 is text, type 1 is image
            if block["type"] == 0 and "lines" in block:
                for line in block.get("lines", []):
                    for span in line.get("spans"):
                        text_block = TextBlock(
                            text=span["text"], bbox=BBox(**span["bbox"])
                        )
                        logger.debug("TextBlock('%s')", span["text"])
                        text_blocks.append(text_block)

        zoom_factor = DPI / 72.0  # 72 is the default DPI for PDF points
        mat = fitz.Matrix(zoom_factor, zoom_factor)
        pix = page.get_pixmap(matrix=mat)
        logger.debug(
            "Pixmap(width=%d, height=%d, size=%d)", pix.width, pix.height, pix.size
        )

        processed_page = ProcessedPage(
            page_number=page_num,
            width=page.rect.width,
            height=page.rect.height,
            zoom_factor=zoom_factor,
            raw_text=raw_text,
            page_image=pix,
            text_blocks=text_blocks,
        )
        pages.append(processed_page)
        logger.debug("Processed page %d/%d in %s", page_num, doc.page_count, doc.name)

    doc.close()

    sha256sum = get_sha256sum(path)
    processed_pdf = ProcessedPDF(filename=path.name, sha256sum=sha256sum, pages=pages)
    logger.info("Processed PDF %s", processed_pdf.filename)
    return processed_pdf
