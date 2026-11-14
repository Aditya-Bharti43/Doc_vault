import logging

from enum import Enum
from pydantic import BaseModel, Field, model_validator,field_validator

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    IDENTITY = "IDENTITY"
    FINANCIAL = "FINANCIAL"
    UTILITY = "UTILITY"
    EDUCATION = "EDUCATION"
    EMPLOYMENT = "EMPLOYMENT"
    INSURANCE = "INSURANCE"
    MEDICAL = "MEDICAL"
    OTHER = "OTHER"


# Controlled taxonomy: category -> allowed subtypes
DOCUMENT_TAXONOMY = {
    DocumentType.IDENTITY: [
        "PAN_CARD",
        "AADHAAR_CARD",
        "PASSPORT",
        "VOTER_ID",
        "DRIVING_LICENSE",
        "OTHER",
    ],
    DocumentType.FINANCIAL: [
        "BANK_STATEMENT",
        "CREDIT_CARD_STATEMENT",
        "SALARY_SLIP",
        "TAX_RETURN",
        "INVOICE",
        "RECEIPT",
        "OTHER",
    ],
    DocumentType.UTILITY: [
        "ELECTRICITY_BILL",
        "WATER_BILL",
        "GAS_BILL",
        "INTERNET_BILL",
        "MOBILE_BILL",
        "OTHER",
    ],
    DocumentType.EDUCATION: [
        "MARKSHEET",
        "DEGREE_CERTIFICATE",
        "TRANSCRIPT",
        "ADMISSION_LETTER",
        "OTHER",
    ],
    DocumentType.EMPLOYMENT: [
        "OFFER_LETTER",
        "EXPERIENCE_LETTER",
        "RELIEVING_LETTER",
        "APPOINTMENT_LETTER",
        "OTHER",
    ],
    DocumentType.INSURANCE: [
        "HEALTH_INSURANCE_POLICY",
        "LIFE_INSURANCE_POLICY",
        "VEHICLE_INSURANCE_POLICY",
        "INSURANCE_PREMIUM_RECEIPT",
        "OTHER",
    ],
    DocumentType.MEDICAL: [
        "PRESCRIPTION",
        "LAB_REPORT",
        "DISCHARGE_SUMMARY",
        "MEDICAL_BILL",
        "OTHER",
    ],
    DocumentType.OTHER: [
        "OTHER",
    ],
}

logger.debug("DOCUMENT_TAXONOMY loaded: %d categories", len(DOCUMENT_TAXONOMY))

class ClassificationResult(BaseModel):
    document_type: DocumentType

    document_subtype: str = Field(
        description="Specific document subtype from the supplied taxonomy."
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    description=(
        "Confidence scores should always be parsed between 0.0 and 1.0 and never a percentage"
    )
    )

    contains_pii: bool = Field(
        description="Whether the document contains personally identifiable information."
    )

    evidence: list[str] = Field(
        description="Short excerpts or indicators from the document supporting the classification."
    )

    reasoning: str = Field(
        description="Brief explanation of why this category and subtype were selected."
    )

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value):
        if isinstance(value, (int, float)) and 1 < value <= 100:
            return value / 100

        return value

    @model_validator(mode="after")
    def validate_subtype(self):
        allowed_subtypes = DOCUMENT_TAXONOMY[self.document_type]

        if self.document_subtype not in allowed_subtypes:
            logger.warning(
                "Invalid subtype for classification result: "
                "document_type=%s document_subtype=%s allowed=%s",
                self.document_type.value,
                self.document_subtype,
                allowed_subtypes,
            )
            raise ValueError(
                f"Subtype '{self.document_subtype}' is not valid "
                f"for category '{self.document_type.value}'"
            )

        logger.debug(
            "Subtype validation passed: document_type=%s document_subtype=%s",
            self.document_type.value,
            self.document_subtype,
        )

        return self