from sqlalchemy import JSON
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Document(Base):

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    document_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, nullable=False
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)

    file_type: Mapped[str] = mapped_column(String(100), nullable=False)

    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)

    status: Mapped[str] = mapped_column(String(30), default="UPLOADED", nullable=False)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    pages = relationship(
        "DocumentPage",
        back_populates="document"
    )


class DocumentPage(Base):
    __tablename__ = "document_pages"

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "page_number",
            name="uq_document_page"
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    document_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("documents.document_id")
    )

    """
    Metadata for storing the fields per page like this 
    {
        "page_number": 1,
        "page_count": 5,
        "format": "PDF",
        "width": 595,
        "height": 842
    }
    """
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    page_number: Mapped[int] = mapped_column(Integer)
    extracted_text: Mapped[str] = mapped_column(Text)

    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="pages"
    )