from app import db
from app.db import database
from app.services.v1_persistence import save_document_pages
from app.services.v1_extraction.extraction_service import extract_pdf_markdown

result = extract_pdf_markdown("storage/90acb580-ce48-4bad-82f1-778ab72355c2.pdf")

save_document_pages(
    db=db,
    document_id=document_id,
    pages=pages
)
for page in result:
    print(f"\nPage: {page['page_number']}")
    print(page["markdown"])