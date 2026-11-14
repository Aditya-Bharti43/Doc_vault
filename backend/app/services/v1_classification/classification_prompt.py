import logging

from app.services.v1_classification.classification_schema import (
    DOCUMENT_TAXONOMY,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a document classification system for Doc-Vault.

Your task is to classify documents based on their content.

Follow these instructions carefully:

1. Identify the broad document category.
2. Identify the most specific applicable document subtype.
3. Use ONLY the categories and subtypes provided in the taxonomy.
4. Do not invent new categories or subtypes.
5. If the document cannot be identified confidently, use:
   document_type = OTHER
   document_subtype = OTHER
6. Use the document's actual content as evidence.
7. Do not assume a document type based only on its filename.
8. If the document contains multiple document types, classify
   it according to its primary purpose.
9. Do not infer missing information.
10. Return only a response matching the supplied JSON schema.

Your confidence score should reflect how strongly the available
document evidence supports your classification.
"""

def build_classification_prompt(document_content: str) -> str:
    logger.debug(
        "Building classification prompt: content_length=%d", len(document_content)
    )

    taxonomy_description = "\n".join(
        f"{category.value}: {', '.join(subtypes)}"
        for category, subtypes in DOCUMENT_TAXONOMY.items()
    )

    prompt = f"""
AVAILABLE DOCUMENT TAXONOMY:

{taxonomy_description}

DOCUMENT CONTENT:

<document>
{document_content}
</document>

CONFIDENCE INSTRUCTIONS:

- Confidence must be a decimal between 0.0 and 1.0.
- 0.0 means no confidence.
- 0.5 means moderate confidence.
- 1.0 means very high confidence.
- Never return confidence as a percentage.
- Example: return 0.95, NOT 95.

Classify this document using the supplied taxonomy.

Return evidence directly supported by the document.
"""

    logger.debug(
        "Classification prompt built: prompt_length=%d taxonomy_categories=%d",
        len(prompt),
        len(DOCUMENT_TAXONOMY),
    )

    return prompt