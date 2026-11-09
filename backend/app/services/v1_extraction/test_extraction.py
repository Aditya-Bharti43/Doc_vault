from app.services.v1_extraction.extraction_service import extract_pdf_markdown

result = extract_pdf_markdown("storage/2b5593bc-391d-4584-b0f8-8e5ceef9377d.pdf")

for page in result:
    print(f"\nPage: {page['page_number']}")
    print(page["markdown"])