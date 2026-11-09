import pymupdf4llm


def extract_pdf_markdown(file_path: str) -> list[dict]:
    try:
        pages = pymupdf4llm.to_markdown(
            file_path,
            page_chunks=True
        )

        extracted_pages = []

        for page_number, page in enumerate(pages, start=1):
            extracted_pages.append({
                "page_number": page_number,
                "markdown": page["text"]
            })

        return extracted_pages

    except Exception as e:
        raise RuntimeError(
            f"PDF Markdown extraction failed: {e}"
        ) from e