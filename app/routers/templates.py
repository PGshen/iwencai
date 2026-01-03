"""
Business templates API router for simple-mode scraping.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.models.schemas import BusinessTemplateCreate, BusinessTemplateResponse, WorkflowTemplateCreate, WorkflowTemplateResponse
from app.models.db_models import BusinessTemplate, WorkflowTemplate
from app.database import get_db
from app.services.workflow import workflow_service

router = APIRouter(prefix="/api/templates", tags=["templates"])
workflows_router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("", response_model=List[BusinessTemplateResponse])
async def list_templates(db: AsyncSession = Depends(get_db)):
    """List all business templates."""
    result = await db.execute(select(BusinessTemplate).order_by(BusinessTemplate.created_at.desc()))
    templates = result.scalars().all()
    return templates


@router.post("", response_model=BusinessTemplateResponse)
async def create_template(
    template: BusinessTemplateCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new business template."""
    # Check if name already exists
    existing = await db.execute(
        select(BusinessTemplate).where(BusinessTemplate.name == template.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Template '{template.name}' already exists")
    
    db_template = BusinessTemplate(**template.model_dump())
    db.add(db_template)
    await db.commit()
    await db.refresh(db_template)
    return db_template


@router.get("/{template_id}", response_model=BusinessTemplateResponse)
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """Get a business template by ID."""
    result = await db.execute(
        select(BusinessTemplate).where(BusinessTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.put("/{template_id}", response_model=BusinessTemplateResponse)
async def update_template(
    template_id: str,
    template_update: BusinessTemplateCreate,
    db: AsyncSession = Depends(get_db)
):
    """Update a business template."""
    result = await db.execute(
        select(BusinessTemplate).where(BusinessTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check name uniqueness if changed
    if template_update.name != template.name:
        existing = await db.execute(
            select(BusinessTemplate).where(BusinessTemplate.name == template_update.name)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Template '{template_update.name}' already exists")
    
    for key, value in template_update.model_dump().items():
        setattr(template, key, value)
    
    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/{template_id}")
async def delete_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a business template."""
    result = await db.execute(
        select(BusinessTemplate).where(BusinessTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    await db.delete(template)
    await db.commit()
    return {"message": "Template deleted successfully"}


# ========== Workflow Templates ==========

@workflows_router.get("", response_model=List[WorkflowTemplateResponse])
async def list_workflows(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WorkflowTemplate).order_by(WorkflowTemplate.created_at.desc()))
    workflows = result.scalars().all()
    return workflows

@workflows_router.post("", response_model=WorkflowTemplateResponse)
async def create_workflow(workflow: WorkflowTemplateCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(WorkflowTemplate).where(WorkflowTemplate.name == workflow.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Workflow '{workflow.name}' already exists")
    db_wf = WorkflowTemplate(**workflow.model_dump())
    db.add(db_wf)
    await db.commit()
    await db.refresh(db_wf)
    try:
        workflow_service.register(db_wf.name, db_wf.definition or {})
    except Exception:
        pass
    return db_wf

@workflows_router.get("/{workflow_id}", response_model=WorkflowTemplateResponse)
async def get_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WorkflowTemplate).where(WorkflowTemplate.id == workflow_id))
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf

@workflows_router.put("/{workflow_id}", response_model=WorkflowTemplateResponse)
async def update_workflow(workflow_id: str, wf_update: WorkflowTemplateCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WorkflowTemplate).where(WorkflowTemplate.id == workflow_id))
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf_update.name != wf.name:
        existing = await db.execute(select(WorkflowTemplate).where(WorkflowTemplate.name == wf_update.name))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Workflow '{wf_update.name}' already exists")
    for k, v in wf_update.model_dump().items():
        setattr(wf, k, v)
    await db.commit()
    await db.refresh(wf)
    try:
        workflow_service.register(wf.name, wf.definition or {})
    except Exception:
        pass
    return wf

@workflows_router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WorkflowTemplate).where(WorkflowTemplate.id == workflow_id))
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    await db.delete(wf)
    await db.commit()
    return {"message": "Workflow deleted successfully"}

# Backward-compatible endpoints under /api/templates/workflows
@router.get("/workflows", response_model=List[WorkflowTemplateResponse])
async def list_workflows_compat(db: AsyncSession = Depends(get_db)):
    return await list_workflows(db)

@router.post("/workflows", response_model=WorkflowTemplateResponse)
async def create_workflow_compat(workflow: WorkflowTemplateCreate, db: AsyncSession = Depends(get_db)):
    return await create_workflow(workflow, db)

@router.get("/workflows/{workflow_id}", response_model=WorkflowTemplateResponse)
async def get_workflow_compat(workflow_id: str, db: AsyncSession = Depends(get_db)):
    return await get_workflow(workflow_id, db)

@router.put("/workflows/{workflow_id}", response_model=WorkflowTemplateResponse)
async def update_workflow_compat(workflow_id: str, wf_update: WorkflowTemplateCreate, db: AsyncSession = Depends(get_db)):
    return await update_workflow(workflow_id, wf_update, db)

@router.delete("/workflows/{workflow_id}")
async def delete_workflow_compat(workflow_id: str, db: AsyncSession = Depends(get_db)):
    return await delete_workflow(workflow_id, db)
