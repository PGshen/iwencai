"""
Batch runner service to execute batch tasks with concurrency and interval.
"""
import asyncio
import csv
import io
import json
import os
from datetime import datetime
from typing import Any
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update

from app.models.db_models import BatchTask, BusinessTemplate, ProxyConfig, CookieConfig, BatchTaskItem
from app.models.schemas import ScrapeRequest
from app.services.scraper import scraper_service
from app.utils.parser import extract_by_json_path
from app.database import async_session

logger = logging.getLogger(__name__)


async def _sleep_ms(ms: int):
    if ms > 0:
        await asyncio.sleep(ms / 1000.0)


def _parse_csv_text(csv_text: str) -> list[dict[str, Any]]:
    f = io.StringIO(csv_text.strip())
    reader = csv.DictReader(f)
    rows = []
    for row in reader:
        clean = {}
        for k, v in row.items():
            if k is None:
                continue
            val = v.strip() if isinstance(v, str) else v
            # Try JSON parse when value looks like JSON
            if isinstance(val, str) and val and (val.startswith("{") or val.startswith("[")):
                try:
                    clean[k] = json.loads(val)
                    continue
                except Exception:
                    pass
            clean[k] = val
        rows.append(clean)
    return rows


RUNNING: dict[str, dict] = {}


def _sanitize_filename(name: str) -> str:
    cleaned = "".join(c for c in name if c.isalnum() or c in ("-", "_", "."))
    return cleaned or "output"


async def stop_batch_task(task_id: str) -> bool:
    ctrl = RUNNING.get(task_id)
    if not ctrl:
        return False
    ctrl["canceled"] = True
    for t in ctrl.get("tasks", []):
        try:
            t.cancel()
        except Exception:
            pass
    return True


async def run_batch_task(task: BatchTask, template: BusinessTemplate):
    out_dir = task.output_dir
    os.makedirs(out_dir, exist_ok=True)
    try:
        concurrency = int(task.concurrency)
    except Exception:
        concurrency = 1
    try:
        sleep_ms = int(task.sleep_ms)
    except Exception:
        sleep_ms = 0
    rows = _parse_csv_text(task.csv_text)
    sem = asyncio.Semaphore(max(1, concurrency))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    RUNNING[task.id] = {"canceled": False, "tasks": []}

    # Initialize items
    # Remove previous items and recreate with pending status using independent session
    async with async_session() as s_init:
        await s_init.execute(delete(BatchTaskItem).where(BatchTaskItem.task_id == task.id))
        for i, row in enumerate(rows):
            item = BatchTaskItem(task_id=task.id, seq_no=str(i + 1), params=row, status="pending")
            s_init.add(item)
        await s_init.commit()
    logger.info(f"Initialized {len(rows)} items for task {task.id}, output_dir={out_dir}")

    async def run_one(idx: int, params_override: dict):
        async with sem:
            async with async_session() as s:
                # Check cancelation
                if RUNNING.get(task.id, {}).get("canceled"):
                    await s.execute(
                        update(BatchTaskItem)
                        .where(BatchTaskItem.task_id == task.id, BatchTaskItem.seq_no == str(idx + 1))
                        .values(status="canceled")
                    )
                    await s.commit()
                    return
                await s.execute(
                    update(BatchTaskItem)
                    .where(BatchTaskItem.task_id == task.id, BatchTaskItem.seq_no == str(idx + 1))
                    .values(status="running")
                )
                await s.commit()
            merged_params = dict(template.default_params or {})
            out_name = params_override.get("output_name")
            params_override.pop("output_name", None)

            merged_params.update(params_override or {})
            from app.services.scraper import scraper_service
            scrape_req = await scraper_service.build_scrape_request_from_template(template, merged_params)

            result = await scraper_service.scrape(scrape_req)
            fname = _sanitize_filename(str(out_name)) + ".json" if out_name else f"{template.name}_{timestamp}_{idx+1}.json"
            fpath = os.path.join(out_dir, fname)
            with open(fpath, "w", encoding="utf-8") as fp:
                if task.data_json_path:
                    try:
                        base = result.data if isinstance(result.data, (dict, list)) else result.raw_response
                        extracted = extract_by_json_path(base, task.data_json_path)
                    except Exception:
                        extracted = None
                    json.dump(extracted, fp, ensure_ascii=False, indent=2)
                else:
                    payload = {}
                    fields = task.save_fields or ["success", "error", "data", "raw_response", "request"]
                    if "success" in fields:
                        payload["success"] = result.success
                    if "error" in fields:
                        payload["error"] = result.error
                    if "data" in fields:
                        data_obj = result.data
                        payload["data"] = data_obj
                    if "raw_response" in fields:
                        payload["raw_response"] = result.raw_response
                    if "request" in fields:
                        payload["request"] = {
                            "url": scrape_req.url,
                            "method": scrape_req.method,
                            "headers": scrape_req.headers,
                            "params": scrape_req.params,
                            "body": scrape_req.body
                        }
                    json.dump(payload, fp, ensure_ascii=False, indent=2)
            logger.info(f"Task {task.id} item {idx+1} saved to {fpath} (success={result.success})")
            try:
                await scraper_service.save_history_from_template(template, merged_params, scrape_req, result)
            except Exception as e:
                logger.exception(f"Save history failed: task={task.id} idx={idx+1} error={e}")
            async with async_session() as s3:
                await s3.execute(
                    update(BatchTaskItem)
                    .where(BatchTaskItem.task_id == task.id, BatchTaskItem.seq_no == str(idx + 1))
                    .values(
                        status="completed" if result.success else "failed",
                        output_file=fpath,
                        error=result.error
                    )
                )
                await s3.commit()
            await _sleep_ms(sleep_ms)

    tasks = [asyncio.create_task(run_one(i, row)) for i, row in enumerate(rows)]
    RUNNING[task.id]["tasks"] = tasks
    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        RUNNING.pop(task.id, None)
        logger.info(f"Task {task.id} finished, removed RUNNING control")
