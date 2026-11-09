
import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import DocumentPage

logger = logging.getLogger(__name__)


def save_document_pages(
    db: Session,
    document_id: str,
    pages: list[dict],
) -> int:
    """
    Persist extracted PDF pages for a document.

    The caller owns the transaction and is responsible
    for committing or rolling back the session.

    Returns:
        Number of pages persisted.
    """

    if not document_id:
        raise ValueError("document_id cannot be empty")

    if not pages:
        raise ValueError(
            f"No extracted pages provided for document {document_id}"
        )

    try:
        extracted_records = []

        for page in pages:
            if not isinstance(page, dict):
                raise ValueError("Each extracted page must be a dictionary")

            page_number = page.get("page_number")
            markdown = page.get("markdown")

            if not isinstance(page_number, int) or page_number < 1:
                raise ValueError(
                    f"Invalid page number: {page_number}"
                )

            if not isinstance(markdown, str):
                raise ValueError(
                    f"Invalid Markdown content on page {page_number}"
                )

            extracted_records.append(
                DocumentPage(
                    document_id=document_id,
                    page_number=page_number,
                    extracted_text=markdown,
                    metadata_json=page.get("metadata"),
                )
            )

        # Replace previously extracted pages.
        db.query(DocumentPage).filter(
            DocumentPage.document_id == document_id
        ).delete(synchronize_session=False)

        db.add_all(extracted_records)

        # Flush sends SQL statements to the database
        # without committing the transaction.
        db.flush()

        logger.info(
            "Successfully persisted %d pages for document_id=%s",
            len(extracted_records),
            document_id,
        )

        return len(extracted_records)

    except ValueError:
        logger.warning(
            "Invalid extracted page data for document_id=%s",
            document_id,
        )
        raise

    except SQLAlchemyError:
        logger.exception(
            "Database error while persisting pages for document_id=%s",
            document_id,
        )
        raise
