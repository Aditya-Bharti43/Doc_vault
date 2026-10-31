from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}
