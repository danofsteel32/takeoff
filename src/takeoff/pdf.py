import logging
from pathlib import Path

import fitz  # PyMuPDF

DPI = 150

logger = logging.getLogger(__name__)


def process(path: Path):
    logger.debug("BEGIN processing %s ...", path.name)

    doc = fitz.open(path)

    logger.debug("Found %d pages in %s", doc.page_count, doc.name)

    pages = []

    for n in range(doc.page_count):
        page_num = n + 1
        logger.debug("Processing page %d/%d in %s", page_num, doc.page_count, doc.name)
        page = doc[n]
        page_data: dict = {}
        page_data["page_number"] = page_num
        page_data["page_width"] = page.rect.width
        page_data["page_height"] = page.rect.height

        logger.debug("Extracting text")

        text = page.get_text("text")
        page_data["full_text"] = text

        logger.info(
            "Extracted %d chars from page %d in %s", len(text), page_num, doc.name
        )

        logger.debug("Extracting text blocks")

        text_blocks_with_bboxes = []
        dict_data = page.get_text("dict")
        blocks = dict_data.get("blocks", [])

        logger.debug("Found %d blocks", len(blocks))

        # blocks -> lines -> spans
        for block in blocks:
            # Block type 0 is text, type 1 is image
            if block["type"] == 0 and "lines" in block:
                for line in block.get("lines", []):
                    for span in line.get("spans"):
                        text_blocks_with_bboxes.append(
                            {"text": span["text"], "bbox": list(span["bbox"])}
                        )
                        logger.debug("Text block '%s'", span["text"])

        page_data["text_blocks"] = text_blocks_with_bboxes

        zoom_factor = DPI / 72.0  # 72 is the default DPI for PDF points
        mat = fitz.Matrix(zoom_factor, zoom_factor)
        pix = page.get_pixmap(matrix=mat, alpha=False)  # alpha=False for JPEG
        # TODO actually do something with the image
        page_data["image"] = str(pix)
        page_data["zoom_factor"] = zoom_factor

        pages.append(page_data)

    doc.close()
    return pages
