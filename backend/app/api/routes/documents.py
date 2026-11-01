import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Document
from app.schemas.document_reponse_schema import DocumentResponse

logger = logging.getLogger(__name__)

router = APIRouter()

STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB (max limit of file size for v1 pipeline)
CHUNK_SIZE = 1024 * 1024  # 1MB

ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}
router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
CHUNK_SIZE = 1024 * 1024  # 1 MB


async def validate_file_signature(file: UploadFile):

    header = await file.read(8)

    # Reset pointer to beginning
    await file.seek(0)

    if header.startswith(b"%PDF"):
        return ".pdf"

    if header.startswith(b"\xff\xd8\xff"):
        return ".jpg"

    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"

    raise HTTPException(status_code=400, detail="Invalid or unsupported file format")


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):

    file_path = None
    document_id = None

    try:
        # Step 1: Validate actual file content
        extension = await validate_file_signature(file)

        # Step 2: Validate filename extension
        original_extension = Path(file.filename or "").suffix.lower()

        allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png"}

        if original_extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail="Invalid file extension")

        # Ensure filename extension matches detected content
        if extension == ".jpg":
            valid_extensions = {".jpg", ".jpeg"}
        else:
            valid_extensions = {extension}

        if original_extension not in valid_extensions:
            raise HTTPException(
                status_code=400, detail="File extension does not match file content"
            )

        # Step 3: Generate unique document ID
        document_id = str(uuid4())

        file_path = STORAGE_DIR / f"{document_id}{extension}"

        # Step 4: Write file in chunks with size restriction
        total_file_size = 0

        with file_path.open("wb") as buffer:

            while chunk := await file.read(CHUNK_SIZE):

                total_file_size += len(chunk)

                if total_file_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413, detail="File size exceeds 10 MB limit"
                    )

                buffer.write(chunk)

        """Storing the metadata of the document in sqlite"""

        document = Document(
            document_id=document_id,
            filename=file.filename,
            file_type=file.content_type,
            file_size=total_file_size,
            storage_path=str(file_path),
            status="UPLOADED",
        )

        """Persist meatadata"""
        db.add(document)
        db.commit()
        db.refresh(document)

        logger.info(
            "Document uploaded: document_id=%s file_size=%d",
            document_id,
            total_file_size,
        )

        return {
            "document_id": document.document_id,
            "filename": document.filename,
            "file_type": document.file_type,
            "file_size": document.file_size,
            "status": document.status,
        }

    except HTTPException as exc:
        logger.warning("Document upload rejected: status_code=%d", exc.status_code)

        db.rollback()

        if file_path is not None and file_path.exists():
            file_path.unlink()

        raise

    except Exception:
        logger.exception(
            "Unexpected error while uploading document: document_id=%s",
            document_id,
        )

        db.rollback()

        if file_path is not None and file_path.exists():
            file_path.unlink()

        raise HTTPException(status_code=500, detail="Failed to upload document")

    finally:
        # Step 6: Close uploaded temporary file
        await file.close()


@router.get("/", response_model=list[DocumentResponse])
def get_documents(db: Session = Depends(get_db)):

    logger.info("Fetching all documents from the database")

    try:
        documents = db.query(Document).order_by(Document.uploaded_at.desc()).all()

        logger.info("Fetched %d documents", len(documents))

        return documents

    except SQLAlchemyError:

        logger.exception("Database error occurred while fetching documents")
        raise HTTPException(status_code=500, detail="Failed to fetch documents")


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_by_id(document_id: str, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.document_id == document_id).first()

    if not document:
        logger.warning("Document not found: document_id=%s", document_id)
        raise HTTPException(status_code=404, detail="Document not found")

    return document


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.document_id == document_id).first()

    if not document:
        logger.warning("Document not found for deletion: document_id=%s", document_id)
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        # Delete the file from storage
        file_path = Path(document.storage_path)
        if file_path.exists():
            file_path.unlink()
            logger.info("Deleted file from storage: %s", file_path)
        else:
            logger.warning(
                "File not found in storage for deletion: %s",
                file_path,
                document_id=document_id,
            )

        # Delete the metadata from the database

        db.delete(document)
        db.commit()

        logger.info("Deleted document metadata: document_id=%s", document_id)

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
