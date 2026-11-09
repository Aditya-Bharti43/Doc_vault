from sqlalchemy import inspect
import logging

from fastapi import FastAPI

from app.api.routes import documents
from app.db.database import Base, engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Doc-Vault API")


Base.metadata.create_all(bind=engine)

inspector = inspect(engine)

print(inspector.get_table_names())
logger.info("Database tables initialized")

app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
