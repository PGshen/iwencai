"""
Configuration management API router.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.models.schemas import (
    ScrapeConfigCreate, ScrapeConfigResponse,
    PushConfigCreate, PushConfigResponse,
    ProxyConfigCreate, ProxyConfigUpdate, ProxyConfigResponse,
    CookieConfigCreate, CookieConfigUpdate, CookieConfigResponse,
    HeaderGroupConfigCreate, HeaderGroupConfigUpdate, HeaderGroupConfigResponse
)
from app.models.db_models import ScrapeConfig, PushConfig, ProxyConfig, CookieConfig, HeaderGroupConfig
from app.database import get_db

router = APIRouter(prefix="/api/configs", tags=["configs"])


# ==================== Scrape Configs ====================

@router.get("/scrape", response_model=List[ScrapeConfigResponse])
async def list_scrape_configs(db: AsyncSession = Depends(get_db)):
    """List all scrape configurations."""
    result = await db.execute(select(ScrapeConfig))
    configs = result.scalars().all()
    return configs


@router.post("/scrape", response_model=ScrapeConfigResponse)
async def create_scrape_config(
    config: ScrapeConfigCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new scrape configuration."""
    db_config = ScrapeConfig(**config.model_dump())
    db.add(db_config)
    await db.commit()
    await db.refresh(db_config)
    return db_config


@router.get("/scrape/{config_id}", response_model=ScrapeConfigResponse)
async def get_scrape_config(config_id: str, db: AsyncSession = Depends(get_db)):
    """Get a scrape configuration by ID."""
    result = await db.execute(
        select(ScrapeConfig).where(ScrapeConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config


@router.put("/scrape/{config_id}", response_model=ScrapeConfigResponse)
async def update_scrape_config(
    config_id: str,
    config_update: ScrapeConfigCreate,
    db: AsyncSession = Depends(get_db)
):
    """Update a scrape configuration."""
    result = await db.execute(
        select(ScrapeConfig).where(ScrapeConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    for key, value in config_update.model_dump().items():
        setattr(config, key, value)
    
    await db.commit()
    await db.refresh(config)
    return config


@router.delete("/scrape/{config_id}")
async def delete_scrape_config(config_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a scrape configuration."""
    result = await db.execute(
        select(ScrapeConfig).where(ScrapeConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    await db.delete(config)
    await db.commit()
    return {"message": "Config deleted successfully"}


# ==================== Push Configs ====================

@router.get("/push", response_model=List[PushConfigResponse])
async def list_push_configs(db: AsyncSession = Depends(get_db)):
    """List all push configurations."""
    result = await db.execute(select(PushConfig))
    configs = result.scalars().all()
    return configs


@router.post("/push", response_model=PushConfigResponse)
async def create_push_config(
    config: PushConfigCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new push configuration."""
    # Ensure unique name
    existing = await db.execute(
        select(PushConfig).where(PushConfig.name == config.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Push config '{config.name}' already exists")
    
    db_config = PushConfig(**config.model_dump())
    db.add(db_config)
    await db.commit()
    await db.refresh(db_config)
    return db_config


@router.get("/push/{config_id}", response_model=PushConfigResponse)
async def get_push_config(config_id: str, db: AsyncSession = Depends(get_db)):
    """Get a push configuration by ID."""
    result = await db.execute(
        select(PushConfig).where(PushConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config


@router.put("/push/{config_id}", response_model=PushConfigResponse)
async def update_push_config(
    config_id: str,
    config_update: PushConfigCreate,
    db: AsyncSession = Depends(get_db)
):
    """Update a push configuration."""
    result = await db.execute(
        select(PushConfig).where(PushConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    # Check name uniqueness if changed
    if config_update.name != config.name:
        existing = await db.execute(
            select(PushConfig).where(PushConfig.name == config_update.name)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Push config '{config_update.name}' already exists")
    
    for key, value in config_update.model_dump().items():
        setattr(config, key, value)
    
    await db.commit()
    await db.refresh(config)
    return config

@router.delete("/push/{config_id}")
async def delete_push_config(config_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a push configuration."""
    result = await db.execute(
        select(PushConfig).where(PushConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    await db.delete(config)
    await db.commit()
    return {"message": "Config deleted successfully"}


@router.get("/proxies", response_model=List[ProxyConfigResponse])
async def list_proxy_configs(db: AsyncSession = Depends(get_db)):
    """List all proxy configurations."""
    result = await db.execute(select(ProxyConfig).order_by(ProxyConfig.updated_at.desc()))
    configs = result.scalars().all()
    return configs

@router.post("/proxies", response_model=ProxyConfigResponse)
async def create_proxy_config(
    config: ProxyConfigCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new proxy configuration."""
    existing = await db.execute(
        select(ProxyConfig).where(ProxyConfig.name == config.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Proxy '{config.name}' already exists")
    db_config = ProxyConfig(
        name=config.name,
        ip=config.ip,
        port=str(config.port),
        scheme=config.scheme,
        enabled=config.enabled
    )
    db.add(db_config)
    await db.commit()
    await db.refresh(db_config)
    return db_config

@router.get("/proxies/{config_id}", response_model=ProxyConfigResponse)
async def get_proxy_config(config_id: str, db: AsyncSession = Depends(get_db)):
    """Get a proxy configuration by ID."""
    result = await db.execute(select(ProxyConfig).where(ProxyConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return config

@router.put("/proxies/{config_id}", response_model=ProxyConfigResponse)
async def update_proxy_config(
    config_id: str,
    update: ProxyConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a proxy configuration."""
    result = await db.execute(select(ProxyConfig).where(ProxyConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Proxy not found")
    if update.name != config.name:
        existing = await db.execute(select(ProxyConfig).where(ProxyConfig.name == update.name))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Proxy '{update.name}' already exists")
    config.name = update.name
    config.ip = update.ip
    config.port = str(update.port)
    config.scheme = update.scheme
    config.enabled = update.enabled
    await db.commit()
    await db.refresh(config)
    return config

@router.delete("/proxies/{config_id}")
async def delete_proxy_config(config_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a proxy configuration."""
    result = await db.execute(select(ProxyConfig).where(ProxyConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Proxy not found")
    await db.delete(config)
    await db.commit()
    return {"message": "Proxy deleted successfully"}

# ==================== Cookie Configs ====================

@router.get("/cookies", response_model=List[CookieConfigResponse])
async def list_cookie_configs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CookieConfig).order_by(CookieConfig.updated_at.desc()))
    return result.scalars().all()

@router.post("/cookies", response_model=CookieConfigResponse)
async def create_cookie_config(config: CookieConfigCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(CookieConfig).where(CookieConfig.name == config.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Cookie '{config.name}' already exists")
    db_config = CookieConfig(**config.model_dump())
    db.add(db_config)
    await db.commit()
    await db.refresh(db_config)
    return db_config

@router.get("/cookies/{config_id}", response_model=CookieConfigResponse)
async def get_cookie_config(config_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CookieConfig).where(CookieConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Cookie not found")
    return config

@router.put("/cookies/{config_id}", response_model=CookieConfigResponse)
async def update_cookie_config(config_id: str, update: CookieConfigUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CookieConfig).where(CookieConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Cookie not found")
    if update.name != config.name:
        existing = await db.execute(select(CookieConfig).where(CookieConfig.name == update.name))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Cookie '{update.name}' already exists")
    for k, v in update.model_dump().items():
        setattr(config, k, v)
    await db.commit()
    await db.refresh(config)
    return config

@router.delete("/cookies/{config_id}")
async def delete_cookie_config(config_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CookieConfig).where(CookieConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Cookie not found")
    await db.delete(config)
    await db.commit()
    return {"message": "Cookie deleted successfully"}

# ==================== Header Group Configs ====================

@router.get("/header-groups", response_model=List[HeaderGroupConfigResponse])
async def list_header_groups(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(HeaderGroupConfig).order_by(HeaderGroupConfig.updated_at.desc()))
    return result.scalars().all()

@router.post("/header-groups", response_model=HeaderGroupConfigResponse)
async def create_header_group(config: HeaderGroupConfigCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(HeaderGroupConfig).where(HeaderGroupConfig.name == config.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Header group '{config.name}' already exists")
    db_config = HeaderGroupConfig(**config.model_dump())
    db.add(db_config)
    await db.commit()
    await db.refresh(db_config)
    return db_config

@router.get("/header-groups/{config_id}", response_model=HeaderGroupConfigResponse)
async def get_header_group(config_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(HeaderGroupConfig).where(HeaderGroupConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Header group not found")
    return config

@router.put("/header-groups/{config_id}", response_model=HeaderGroupConfigResponse)
async def update_header_group(config_id: str, update: HeaderGroupConfigUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(HeaderGroupConfig).where(HeaderGroupConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Header group not found")
    if update.name != config.name:
        existing = await db.execute(select(HeaderGroupConfig).where(HeaderGroupConfig.name == update.name))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Header group '{update.name}' already exists")
    for k, v in update.model_dump().items():
        setattr(config, k, v)
    await db.commit()
    await db.refresh(config)
    return config

@router.delete("/header-groups/{config_id}")
async def delete_header_group(config_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(HeaderGroupConfig).where(HeaderGroupConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Header group not found")
    await db.delete(config)
    await db.commit()
    return {"message": "Header group deleted successfully"}
