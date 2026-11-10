from sqlalchemy import inspect
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import documents
from app.db.database import Base, engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Doc-Vault API")


# ---------------------------------------------------------------------------
# Database initialisation
# ---------------------------------------------------------------------------
try:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    logger.info("Database tables initialised: %s", table_names)
except Exception:
    logger.critical("Failed to initialise database tables", exc_info=True)
    raise


# ---------------------------------------------------------------------------
# Request / response lifecycle logging
# ---------------------------------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("Incoming request: method=%s path=%s", request.method, request.url.path)
    response = await call_next(request)
    logger.info(
        "Outgoing response: method=%s path=%s status_code=%d",
        request.method,
        request.url.path,
        response.status_code,
    )
    return response


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
logger.info("Router registered: prefix=/api/v1/documents")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    logger.debug("Health check called")
    return {"status": "healthy"}
