import logging

import pymupdf4llm

logger = logging.getLogger(__name__)


def extract_pdf_markdown(file_path: str) -> list[dict]:
    logger.info("Starting PDF extraction: file_path=%s", file_path)

    try:
        pages = pymupdf4llm.to_markdown(
            file_path,
            page_chunks=True
        )

        logger.debug("pymupdf4llm returned %d raw page chunks", len(pages))

        extracted_pages = []

        for page_number, page in enumerate(pages, start=1):

            metadata = page.get("metadata", {})

            extracted_pages.append({
                "page_number": page_number,
                "markdown": page["text"],
                "metadata": metadata
            })

            logger.debug(
                "Extracted page %d: char_count=%d metadata_keys=%s",
                page_number,
                len(page["text"]),
                list(metadata.keys()),
            )

        logger.info(
            "PDF extraction complete: file_path=%s total_pages=%d",
            file_path,
            len(extracted_pages),
        )

        return extracted_pages

    except Exception as e:
        logger.exception(
            "PDF Markdown extraction failed: file_path=%s error=%s",
            file_path,
            e,
        )
        raise RuntimeError(
            f"PDF Markdown extraction failed: {e}"
        ) from e