import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Document
from app.schemas.document_reponse_schema import DocumentResponse
from app.services.doc_processing_service import process_pdf_document
logger = logging.getLogger(__name__)

router = APIRouter()

STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
CHUNK_SIZE = 1024 * 1024           # 1 MB

ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}
router = APIRouter()

mime_types = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".png": "image/png",
}


async def validate_file_signature(file: UploadFile) -> str:
    """
    Reads the first 8 bytes to detect the true file type from its magic bytes.
    Raises HTTP 400 for unrecognised signatures.
    """
    logger.debug("Validating file signature: filename=%s", file.filename)

    header = await file.read(8)

    # Reset pointer to beginning
    await file.seek(0)

    if header.startswith(b"%PDF"):
        logger.debug("Detected file type: PDF")
        return ".pdf"

    if header.startswith(b"\xff\xd8\xff"):
        logger.debug("Detected file type: JPEG")
        return ".jpg"

    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        logger.debug("Detected file type: PNG")
        return ".png"

    logger.warning(
        "Rejected upload — unrecognised magic bytes: filename=%s header=%s",
        file.filename,
        header.hex(),
    )
    raise HTTPException(status_code=400, detail="Invalid or unsupported file format")


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):

    file_path = None
    document_id = None
    document_saved = False

    logger.info("Upload request received: filename=%s content_type=%s", file.filename, file.content_type)

    try:
        # Step 1: Validate actual file content
        extension = await validate_file_signature(file)

        # Step 2: Validate filename extension
        original_extension = Path(file.filename or "").suffix.lower()

        allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png"}

        if original_extension not in allowed_extensions:
            logger.warning(
                "Rejected upload — invalid extension: filename=%s extension=%s",
                file.filename,
                original_extension,
            )
            raise HTTPException(status_code=400, detail="Invalid file extension")

        # Ensure filename extension matches detected content
        if extension == ".jpg":
            valid_extensions = {".jpg", ".jpeg"}
        else:
            valid_extensions = {extension}

        if original_extension not in valid_extensions:
            logger.warning(
                "Rejected upload — extension/content mismatch: "
                "filename=%s declared_ext=%s detected_ext=%s",
                file.filename,
                original_extension,
                extension,
            )
            raise HTTPException(
                status_code=400, detail="File extension does not match file content"
            )

        # Step 3: Generate unique document ID
        document_id = str(uuid4())

        file_path = STORAGE_DIR / f"{document_id}{extension}"
        logger.info("Assigned document_id=%s storage_path=%s", document_id, file_path)

        # Step 4: Write file in chunks with size restriction
        total_file_size = 0

        with file_path.open("wb") as buffer:

            while chunk := await file.read(CHUNK_SIZE):

                total_file_size += len(chunk)

                if total_file_size > MAX_FILE_SIZE:
                    logger.warning(
                        "Rejected upload — file too large: document_id=%s size_so_far=%d",
                        document_id,
                        total_file_size,
                    )
                    raise HTTPException(
                        status_code=413, detail="File size exceeds 10 MB limit"
                    )

                buffer.write(chunk)

        logger.info(
            "File written to disk: document_id=%s file_size=%d path=%s",
            document_id,
            total_file_size,
            file_path,
        )

        # Step 5: Persist document metadata
        document = Document(
            document_id=document_id,
            filename=file.filename,
            file_type=mime_types[extension],
            file_size=total_file_size,
            storage_path=str(file_path),
            status="UPLOADED",
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        document_saved = True

        logger.info(
            "Document metadata persisted: document_id=%s filename=%s file_size=%d",
            document_id,
            file.filename,
            total_file_size,
        )

        # Step 6: Process PDFs (extract text)
        if extension == ".pdf":
            logger.info("Triggering PDF processing: document_id=%s", document_id)
            process_pdf_document(
                db=db,
                document_id=document_id,
                file_path=str(file_path),
            )
            db.refresh(document)
            logger.info(
                "PDF processing finished: document_id=%s status=%s",
                document_id,
                document.status,
            )

        # Images will be handled by the OCR pipeline later.

        return {
            "document_id": document.document_id,
            "filename": document.filename,
            "file_type": document.file_type,
            "file_size": document.file_size,
            "status": document.status,
        }

    except HTTPException as exc:
        logger.warning(
            "Upload rejected: document_id=%s status_code=%d detail=%s",
            document_id,
            exc.status_code,
            exc.detail,
        )
        db.rollback()

        # Delete only if the document wasn't successfully committed
        if not document_saved and file_path is not None:
            try:
                file_path.unlink(missing_ok=True)
                logger.info("Cleaned up partial file: path=%s", file_path)
            except OSError:
                logger.exception(
                    "Failed to clean up uploaded file: document_id=%s path=%s",
                    document_id,
                    file_path,
                )

        raise

    except Exception:
        db.rollback()

        logger.exception(
            "Unexpected error during document upload: document_id=%s",
            document_id,
        )

        if not document_saved and file_path is not None:
            try:
                file_path.unlink(missing_ok=True)
                logger.info("Cleaned up partial file: path=%s", file_path)
            except OSError:
                logger.exception(
                    "Failed to clean up uploaded file: document_id=%s path=%s",
                    document_id,
                    file_path,
                )

        raise HTTPException(
            status_code=500,
            detail="Failed to upload document",
        )

    finally:
        await file.close()
        logger.debug("Upload file handle closed: filename=%s", file.filename)


@router.get("/", response_model=list[DocumentResponse])
def get_documents(db: Session = Depends(get_db)):

    logger.info("Fetching all documents")

    try:
        documents = db.query(Document).order_by(Document.uploaded_at.desc()).all()

        logger.info("Fetched %d documents", len(documents))

        return documents

    except SQLAlchemyError:
        logger.exception("Database error occurred while fetching documents")
        raise HTTPException(status_code=500, detail="Failed to fetch documents")


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_by_id(document_id: str, db: Session = Depends(get_db)):
    logger.info("Fetching document: document_id=%s", document_id)

    document = db.query(Document).filter(Document.document_id == document_id).first()

    if not document:
        logger.warning("Document not found: document_id=%s", document_id)
        raise HTTPException(status_code=404, detail="Document not found")

    logger.info(
        "Document found: document_id=%s filename=%s status=%s",
        document_id,
        document.filename,
        document.status,
    )
    return document


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    logger.info("Delete request: document_id=%s", document_id)

    document = db.query(Document).filter(Document.document_id == document_id).first()

    if not document:
        logger.warning("Document not found for deletion: document_id=%s", document_id)
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        # Delete the file from storage
        file_path = Path(document.storage_path)
        if file_path.exists():
            file_path.unlink()
            logger.info("Deleted file from storage: path=%s", file_path)
        else:
            logger.warning(
                "File not found in storage during deletion: path=%s document_id=%s",
                file_path,
                document_id,
            )

        # Delete the metadata from the database
        db.delete(document)
        db.commit()

        logger.info("Document deleted: document_id=%s", document_id)

        return {"detail": "Document deleted successfully", "document_id": document_id}

    except HTTPException:
        raise

    except SQLAlchemyError:
        db.rollback()

        logger.exception("Database error while deleting document_id=%s", document_id)

        raise HTTPException(status_code=500, detail="Failed to delete document")

    except OSError:
        logger.exception("File system error while deleting document_id=%s", document_id)

        raise HTTPException(status_code=500, detail="Failed to delete document file")
