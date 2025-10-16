import json
import logging
from pathlib import Path

import pymupdf as fitz  # type: ignore[import-untyped]
from attrs import define
from cattrs.preconf.json import make_converter

from .utils import get_sha256sum

DPI = 150
STORAGE_DIR = Path(".cache")

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


@define
class StorageBackend:
    """Saves the text and images extracted from a PDF to the filesystem.

    Each sheet has at least 2 files, the text in a json file and the sheet
    rendered as an image. More text and image crops will be created as needed.
    """

    directory: Path


converter = make_converter()


@converter.register_unstructure_hook
def pixmap_hook(pix: fitz.Pixmap) -> str:
    """Returns md5hash of the Pixmap."""
    digest: bytes = pix.digest
    return digest.hex()


def load(path: Path) -> None:
    sha256sum = get_sha256sum(path)
    sub_dir = STORAGE_DIR / sha256sum
    logger.debug("Loading %s from %s/%s ...", path, STORAGE_DIR, sha256sum)

    if not sub_dir.exists():
        logger.debug("%s has not been processed", path)
        raise FileNotFoundError(path)

    logger.info("TODO actually load the PDF")


def store(processed_pdf: ProcessedPDF) -> None:
    sub_dir = STORAGE_DIR / processed_pdf.sha256sum
    sub_dir.mkdir(exist_ok=True, parents=True)
    logger.debug(
        "Storing %s in %s/%s",
        processed_pdf.filename,
        STORAGE_DIR,
        processed_pdf.sha256sum,
    )

    for page in processed_pdf.pages:
        page_dir = sub_dir / str(page.page_number)
        page_dir.mkdir(exist_ok=True)
        text_file = page_dir / "text.json"
        data = converter.unstructure(page)
        with open(text_file, "w") as f:
            json.dump(data, f, indent=2)
        logger.debug("Wrote %s", text_file)
        image_file = page_dir / "image.png"
        page.page_image.save(image_file)
        logger.debug("Wrote %s", image_file)

    logger.info(
        "Saved %s in %s/%s",
        processed_pdf.filename,
        STORAGE_DIR,
        processed_pdf.sha256sum,
    )


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
                            text=span["text"], bbox=BBox(*span["bbox"])
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
