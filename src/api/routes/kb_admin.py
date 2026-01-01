"""Knowledge base admin API routes."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.core.logging import get_logger
from src.services.kb_ingestion import kb_ingestion_service
from src.services.vector_store import vector_store

logger = get_logger(__name__)

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


class IngestTextRequest(BaseModel):
    """Request model for ingesting text."""

    tenant_id: str
    text: str
    document_name: str
    category: str = "general"
    tags: Optional[list[str]] = None


@router.post("/documents")
async def upload_document(
    tenant_id: str = Form(...),
    file: UploadFile = File(...),
    category: str = Form("general"),
    tags: Optional[str] = Form(None),
):
    """
    Upload and ingest a document into the knowledge base.

    Args:
        tenant_id: Tenant identifier
        file: Document file to upload
        category: Document category
        tags: Comma-separated tags

    Returns:
        Ingestion result
    """
    try:
        tag_list = [tag.strip() for tag in tags.split(",")] if tags else None

        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)

        file_path = upload_dir / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        result = await kb_ingestion_service.ingest_document(
            tenant_id=tenant_id,
            file_path=file_path,
            category=category,
            tags=tag_list,
        )

        file_path.unlink()

        return {"status": "success", **result}

    except Exception as e:
        logger.error("Failed to upload document", tenant_id=tenant_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to ingest document: {str(e)}")


@router.post("/text")
async def ingest_text(request: IngestTextRequest):
    """
    Ingest raw text into the knowledge base.

    Args:
        request: Ingest text request

    Returns:
        Ingestion result
    """
    try:
        result = await kb_ingestion_service.ingest_text(
            tenant_id=request.tenant_id,
            text=request.text,
            document_name=request.document_name,
            category=request.category,
            tags=request.tags,
        )

        return {"status": "success", **result}

    except Exception as e:
        logger.error("Failed to ingest text", tenant_id=request.tenant_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to ingest text: {str(e)}")


@router.get("/stats/{tenant_id}")
async def get_kb_stats(tenant_id: str):
    """
    Get knowledge base statistics for a tenant.

    Args:
        tenant_id: Tenant identifier

    Returns:
        KB statistics
    """
    try:
        stats = vector_store.get_collection_stats(tenant_id)
        return {"status": "success", **stats}

    except Exception as e:
        logger.error("Failed to get KB stats", tenant_id=tenant_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.delete("/tenant/{tenant_id}")
async def delete_tenant_kb(tenant_id: str):
    """
    Delete all knowledge base data for a tenant.

    Args:
        tenant_id: Tenant identifier

    Returns:
        Deletion result
    """
    try:
        vector_store.delete_collection(tenant_id)
        return {"status": "success", "message": f"Deleted KB for tenant {tenant_id}"}

    except Exception as e:
        logger.error("Failed to delete tenant KB", tenant_id=tenant_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete KB: {str(e)}")

