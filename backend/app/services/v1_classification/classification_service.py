import logging

from langchain.chat_models import init_chat_model

from app.services.v1_classification.classification_schema import (
    ClassificationResult,
)

from app.services.v1_classification.classification_prompt import (
    SYSTEM_PROMPT,
    build_classification_prompt,
)

logger = logging.getLogger(__name__)


class ClassificationService:

    def __init__(self):
        logger.info(
            "Initialising ClassificationService: model=ollama:qwen2.5:1.5b temperature=0"
        )

        try:
            self.model = init_chat_model(
                "ollama:qwen2.5:1.5b",
                temperature=0
            )

            self.structured_model = self.model.with_structured_output(
                ClassificationResult
            )

            logger.info("ClassificationService initialised successfully")

        except Exception:
            logger.exception("Failed to initialise ClassificationService")
            raise

    def classify_document(self, document_content: str) -> ClassificationResult:
        logger.info(
            "Classification request received: content_length=%d",
            len(document_content),
        )

        if not document_content.strip():
            logger.warning("Classification rejected: document content is empty")
            raise ValueError("Document content cannot be empty.")

        messages = [
            ("system", SYSTEM_PROMPT),
            ("human", build_classification_prompt(document_content)),
        ]

        logger.debug("Invoking structured model for classification")

        try:
            result = self.structured_model.invoke(messages)
        except Exception:
            logger.exception(
                "Structured model invocation failed: content_length=%d",
                len(document_content),
            )
            raise

        logger.info(
            "Classification complete: document_type=%s document_subtype=%s "
            "confidence=%.2f contains_pii=%s",
            result.document_type.value,
            result.document_subtype,
            result.confidence,
            result.contains_pii,
        )

        logger.debug("Classification reasoning: %s", result.reasoning)

        return result