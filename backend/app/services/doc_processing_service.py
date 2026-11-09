
import logging

from sqlalchemy.orm import Session

from app.db.models import Document
from app.services.v1_extraction.extraction_service import (
    extract_pdf_markdown,
)
from app.services.v1_persistence.doc_content_persistence import (
    save_document_pages,
)

logger = logging.getLogger(__name__)


def process_pdf_document(
    db: Session,
    document_id: str,
    file_path: str,
) -> bool:
    """
    Extract and persist PDF pages.

    Returns True on success and False on processing failure.
    The original uploaded file and Document record are retained
    even if processing fails.
    """

    document = db.query(Document).filter(
        Document.document_id == document_id
    ).first()

    if document is None:
        logger.error(
            "Cannot process document: document not found, document_id=%s",
            document_id,
        )
        return False

    try:
        document.status = "PROCESSING"
        db.commit()

        logger.info(
            "PDF processing started: document_id=%s",
            document_id,
        )

        # 1. Extract Markdown and metadata
        pages = extract_pdf_markdown(file_path)

        if not pages:
            raise ValueError("PDF extraction returned no pages")

        # 2. Persist extracted pages
        saved_count = save_document_pages(
            db=db,
            document_id=document_id,
            pages=pages,
        )

        # 3. Update processing status
        document.status = "PROCESSED"

        # Commit page records and status together
        db.commit()

        logger.info(
            "PDF processing completed: document_id=%s pages=%d",
            document_id,
            saved_count,
        )

        return True

    except Exception:
        db.rollback()

        logger.exception(
            "PDF processing failed: document_id=%s",
            document_id,
        )

        # Mark the document as FAILED in a fresh transaction
        try:
            document = db.query(Document).filter(
                Document.document_id == document_id
            ).first()

            if document is not None:
                document.status = "FAILED"
                db.commit()

        except Exception:
            db.rollback()
            logger.exception(
                "Could not update document status to FAILED: document_id=%s",
                document_id,
            )

        return False
