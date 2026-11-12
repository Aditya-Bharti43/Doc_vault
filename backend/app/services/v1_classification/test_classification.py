
from app.services.v1_classification.classification_service import (
    ClassificationService,
)


def main():
    service = ClassificationService()

    sample_document = """
    GOVERNMENT OF INDIA
    INCOME TAX DEPARTMENT

    PERMANENT ACCOUNT NUMBER

    Name: Rahul Kumar
    PAN: ABCDE1234F
    Date of Birth: 15-05-2000
    """

    result = service.classify_document(sample_document)

    print("\nClassification Result:")
    print(result.model_dump_json(indent=4))


if __name__ == "__main__":
    main()
