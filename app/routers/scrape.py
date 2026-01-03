"""
Scrape API router with simple and advanced modes.
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete, or_, func
from typing import List, Optional
from datetime import datetime
import math

from app.models.schemas import (
    ScrapeRequest, ScrapeResponse,
    SimpleScrapeRequest, SimpleScrapeResponse,
    ScrapeHistoryResponse, ScrapeHistoryPaginatedResponse
)
from app.models.db_models import ScrapeConfig, BusinessTemplate, ScrapeHistory, ProxyConfig, CookieConfig
from app.services.scraper import scraper_service
from app.database import get_db
from app.services.workflow import workflow_service

router = APIRouter(prefix="/api", tags=["scrape"])


async def save_history(
    db: AsyncSession,
    template_id: Optional[str],
    template_name: Optional[str],
    url: str,
    method: str,
    params: Optional[dict],
    headers: Optional[dict],
    body: Optional[dict],
    api_headers: Optional[dict],
    api_params: Optional[dict],
    api_body: Optional[dict],
    success: bool,
    data: Optional[dict],
    raw_response: Optional[dict],
    error: Optional[str]
):
    """Save scrape result to history."""
    history = ScrapeHistory(
        template_id=template_id,
        template_name=template_name,
        url=url,
        method=method,
        request_params=params,
        request_headers=headers,
        request_body=body,
        api_request_headers=api_headers,
        api_request_params=api_params,
        api_request_body=api_body,
        success=success,
        response_data=data,
        raw_response=raw_response,
        error_message=error
    )
    db.add(history)
    await db.commit()


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_data(
    request: ScrapeRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
) -> ScrapeResponse:
    """
    [Advanced Mode] Scrape data from an external API.
    
    You can either:
    1. Provide full request parameters (url, method, headers, etc.)
    2. Use a pre-configured config by providing config_id
    """
    # If config_id is provided, load from database
    if request.config_id:
        result = await db.execute(
            select(ScrapeConfig).where(ScrapeConfig.id == request.config_id)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            return ScrapeResponse(
                success=False,
                error=f"Config not found: {request.config_id}"
            )
        
        # Build request from saved config, allowing overrides
        request = ScrapeRequest(
            url=request.url or config.url,
            method=request.method or config.method,
            headers=request.headers or config.headers,
            params=request.params or config.params,
            body=request.body or config.body,
            extract_type=request.extract_type if request.extract_type != "python" else config.extract_type,
            json_path=request.json_path or config.json_path,
            parser_code=request.parser_code or config.parser_code
        )
    
    response = await scraper_service.scrape(request)
    
    # Save to history
    await save_history(
        db=db,
        template_id=None,
        template_name=None,
        url=request.url or "",
        method=request.method,
        params=request.params,
        headers=request.headers,
        body=request.body,
        api_headers=dict(http_request.headers),
        api_params=request.params,
        api_body=request.model_dump(),
        success=response.success,
        data=response.data if response.success else None,
        raw_response=response.raw_response,
        error=response.error
    )
    
    return response


@router.post("/scrape/simple", response_model=SimpleScrapeResponse)
async def simple_scrape(
    request: SimpleScrapeRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
) -> SimpleScrapeResponse:
    """
    [Simple Mode] Scrape data using a pre-configured business template.
    
    User only needs to provide template_name and optional params.
    """
    # Find business template by name; if not found, try workflow registry
    result = await db.execute(
        select(BusinessTemplate).where(BusinessTemplate.name == request.template_name)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        # Execute a registered workflow (composed of business templates)
        wf_resp = await workflow_service.execute(request.template_name, request.params or {})
        return SimpleScrapeResponse(
            success=wf_resp.success,
            template_name=request.template_name,
            data=wf_resp.data,
            error=wf_resp.error
        )
    
    merged_params = dict(template.default_params or {})
    merged_params.update(request.params or {})
    from app.services.scraper import scraper_service
    scrape_request = await scraper_service.build_scrape_request_from_template(template, merged_params)
    
    response = await scraper_service.scrape(scrape_request)
    
    # Save to history
    await save_history(
        db=db,
        template_id=template.id,
        template_name=template.name,
        url=template.url,
        method=template.method,
        params=merged_params,
        headers=template.headers,
        body=template.body_template,
        api_headers=dict(http_request.headers),
        api_params=request.params,
        api_body={"template_name": request.template_name, "params": request.params},
        success=response.success,
        data=response.data if response.success else None,
        raw_response=response.raw_response,
        error=response.error
    )
    
    return SimpleScrapeResponse(
        success=response.success,
        template_name=request.template_name,
        data=response.data,
        error=response.error
    )


@router.get("/scrape/history", response_model=ScrapeHistoryPaginatedResponse)
async def get_scrape_history(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    keyword: Optional[str] = Query(None, description="Search keyword in URL or template name"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    status: Optional[str] = Query(None, description="Filter by status (success/failed)"),
    start_time: Optional[datetime] = Query(None, description="Filter start time"),
    end_time: Optional[datetime] = Query(None, description="Filter end time"),
    db: AsyncSession = Depends(get_db)
) -> ScrapeHistoryPaginatedResponse:
    """Get scrape history records with pagination and filtering."""
    # Base query
    query = select(ScrapeHistory)
    
    # Filters
    if keyword:
        query = query.where(
            or_(
                ScrapeHistory.url.contains(keyword),
                ScrapeHistory.template_name.contains(keyword)
            )
        )
    
    if method and method != "ALL":
        query = query.where(ScrapeHistory.method == method)
        
    if status and status != "ALL":
        is_success = (status.lower() == "success")
        query = query.where(ScrapeHistory.success == is_success)
    
    if start_time:
        query = query.where(ScrapeHistory.created_at >= start_time)
        
    if end_time:
        query = query.where(ScrapeHistory.created_at <= end_time)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()

    # Pagination
    query = query.order_by(desc(ScrapeHistory.created_at))
    query = query.offset((page - 1) * size).limit(size)
    
    result = await db.execute(query)
    histories = result.scalars().all()
    
    pages = math.ceil(total / size) if size > 0 else 0
    
    return ScrapeHistoryPaginatedResponse(
        items=histories,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.delete("/scrape/history")
async def clear_scrape_history(db: AsyncSession = Depends(get_db)):
    """Clear all scrape history."""
    await db.execute(delete(ScrapeHistory))
    await db.commit()
    return {"message": "History cleared successfully"}
