from __future__ import annotations
from typing import Any, Dict, Optional
from dataclasses import dataclass
import random
import asyncio

from sqlalchemy import select

from app.database import async_session
from app.models.db_models import BusinessTemplate
from app.models.schemas import ScrapeResponse
from app.utils.parser import extract_by_json_path
from app.services.scraper import scraper_service


@dataclass
class WorkflowStep:
    name: str
    template_name: str
    input_map: Dict[str, Any]
    extract_map: Optional[Dict[str, str]] = None
    retry: int = 3
    sleep_min_seconds: int = 0
    sleep_max_seconds: int = 0


class WorkflowService:
    def __init__(self):
        self.registry: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, definition: Dict[str, Any]):
        self.registry[name] = definition
    
    async def refresh_from_db(self):
        from app.models.db_models import WorkflowTemplate
        async with async_session() as s:
            res = await s.execute(select(WorkflowTemplate))
            workflows = res.scalars().all()
            for wf in workflows:
                try:
                    if isinstance(wf.definition, dict):
                        self.registry[wf.name] = wf.definition
                except Exception:
                    pass

    def _rand_sleep(self, min_s: int, max_s: int):
        if max_s <= 0:
            return 0
        if min_s < 0:
            min_s = 0
        if max_s < min_s:
            max_s = min_s
        return random.randint(min_s, max_s)

    def _resolve_value(self, context: Dict[str, Any], val: Any) -> Any:
        if isinstance(val, str):
            s = val.strip()
            if s.startswith("$random(") and s.endswith(")"):
                inside = s[len("$random(") : -1]
                parts = [p.strip() for p in inside.split(",")]
                if len(parts) == 2:
                    try:
                        lo = int(parts[0])
                        hi = int(parts[1])
                        return str(random.randint(lo, hi))
                    except Exception:
                        return str(random.randint(1_000_000_000, 9_999_999_999))
                return str(random.randint(1_000_000_000, 9_999_999_999))
            if s.startswith("$."):
                try:
                    return extract_by_json_path(context, s[2:])
                except Exception:
                    return None
        return val

    async def _get_template_by_name(self, name: str) -> Optional[BusinessTemplate]:
        async with async_session() as s:
            res = await s.execute(select(BusinessTemplate).where(BusinessTemplate.name == name))
            return res.scalar_one_or_none()

    async def execute(self, workflow_name: str, params: Dict[str, Any]) -> ScrapeResponse:
        wf_def = self.registry.get(workflow_name)
        if not wf_def:
            return ScrapeResponse(success=False, error=f"Workflow not found: {workflow_name}")

        steps_def = wf_def.get("steps") or []
        context: Dict[str, Any] = {"params": params, "steps": {}}
        last_response: Optional[ScrapeResponse] = None

        for idx, sdef in enumerate(steps_def, start=1):
            name = sdef.get("name") or f"step{idx}"
            template_name = sdef.get("template_name")
            input_map = sdef.get("input") or {}
            extract_map = sdef.get("extract") or None
            retry = int(sdef.get("retry") or 3)
            sleep_min = int(sdef.get("sleep", {}).get("min") or 0)
            sleep_max = int(sdef.get("sleep", {}).get("max") or 0)

            if not template_name:
                return ScrapeResponse(success=False, error=f"Workflow step missing template_name: {name}")

            tpl = await self._get_template_by_name(template_name)
            if not tpl:
                return ScrapeResponse(success=False, error=f"Template not found in workflow: {template_name}")

            # Build step params by resolving input_map against current context
            step_params: Dict[str, Any] = {}
            for k, v in input_map.items():
                step_params[k] = self._resolve_value(context, v)

            attempt = 0
            resp: Optional[ScrapeResponse] = None
            while attempt < retry:
                attempt += 1
                scrape_req = await scraper_service.build_scrape_request_from_template(tpl, step_params)
                resp = await scraper_service.scrape(scrape_req)
                # Decide success: data exists or success True
                if resp.success and (resp.data is not None):
                    break
                # sleep before retry
                wait_s = self._rand_sleep(sleep_min, sleep_max)
                if wait_s > 0:
                    await asyncio.sleep(wait_s)

            last_response = resp
            if not last_response or not last_response.success or last_response.data is None:
                err = None if not last_response else last_response.error
                return ScrapeResponse(success=False, error=err or f"Workflow step failed: {name}", raw_response=last_response.raw_response if last_response else None)

            # Extract and stash into context for downstream steps
            extracted: Dict[str, Any] = {}
            if extract_map:
                for out_key, path in extract_map.items():
                    val = None
                    p = path
                    if isinstance(p, str) and p.startswith("$."):
                        p = p[2:]
                    try:
                        if last_response.data is not None:
                            val = extract_by_json_path(last_response.data, p)
                    except Exception:
                        val = None
                    if val is None and last_response.raw_response is not None:
                        try:
                            val = extract_by_json_path(last_response.raw_response, p)
                        except Exception:
                            val = None
                    extracted[out_key] = val
            context["steps"][name] = {"params": step_params, "extracted": extracted, "data": last_response.data}

            # sleep between steps (if configured)
            wait_s = self._rand_sleep(sleep_min, sleep_max)
            if wait_s > 0:
                await asyncio.sleep(wait_s)

        return last_response or ScrapeResponse(success=False, error="No steps executed")


# Singleton
workflow_service = WorkflowService()

# Built-in example registry entry for iwencai two-step flow
workflow_service.register(
    "iwencai-two-step",
    {
        "description": "先调用get-robot-data获取condition/token，再调用iwencai_export获取最终数据",
        "steps": [
            {
                "name": "step1",
                "template_name": "get-robot-data",
                "input": {
                    "question": "$.params.question"
                },
                "extract": {
                    "condition": "$.condition",
                    "token": "$.token"
                },
                "retry": 5,
                "sleep": {"min": 2, "max": 3}
            },
            {
                "name": "step2",
                "template_name": "iwencai_export",
                "input": {
                    "query": "$.params.question",
                    "condition": "$.steps.step1.extracted.condition",
                    "iwc_token": "$.steps.step1.extracted.token",
                    "randomStr": "$random(1000000000,9999999999)"
                },
                "retry": 5,
                "sleep": {"min": 5, "max": 15}
            }
        ]
    }
)
