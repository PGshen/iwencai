from sqlalchemy import select
from app.database import async_session
from app.models.db_models import BusinessTemplate, CookieConfig, ProxyConfig, HeaderGroupConfig
import httpx
from typing import Any, Optional
from app.models.schemas import ScrapeRequest, ScrapeResponse
from app.utils.parser import execute_parser, extract_by_json_path, ParserExecutionError, ParserTimeoutError
from app.config import get_settings
from app.models.db_models import ScrapeHistory
import urllib.parse


class ScraperService:
    """Service for scraping data from external APIs."""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def build_scrape_request_from_template(self, template: BusinessTemplate, user_params: dict[str, Any]) -> ScrapeRequest:
        merged_params = dict(template.default_params or {})
        headers_obj = template.headers or {}
        ct = ""
        for k, v in headers_obj.items():
            if k.lower() == "content-type":
                ct = v.lower()
                break
        body_obj = template.body_template
        if isinstance(body_obj, dict):
            body_merged = dict(body_obj)
            is_form_body = False
        elif isinstance(body_obj, str) and ("application/x-www-form-urlencoded" in ct):
            try:
                pairs = urllib.parse.parse_qsl(body_obj, keep_blank_values=True)
                body_merged = dict(pairs)
                is_form_body = True
            except Exception:
                body_merged = body_obj
                is_form_body = False
        else:
            body_merged = body_obj
            is_form_body = False
        up = user_params or {}
        for k, v in up.items():
            in_params = k in merged_params
            in_body = isinstance(body_merged, dict) and (k in body_merged)
            if in_params:
                merged_params[k] = v
            if in_body:
                body_merged[k] = v
            if (not in_params) and (not in_body):
                if (template.method or "GET").upper() == "POST":
                    if isinstance(body_merged, dict):
                        body_merged[k] = v
                    elif body_merged is None:
                        body_merged = {k: v}
                    else:
                        merged_params[k] = v
                else:
                    merged_params[k] = v
        if is_form_body and isinstance(body_merged, dict):
            try:
                body_out = urllib.parse.urlencode(body_merged, doseq=True)
            except Exception:
                body_out = body_merged
        else:
            body_out = body_merged
        req = ScrapeRequest(
            url=template.url,
            method=template.method,
            headers=template.headers,
            params=merged_params,
            body=body_out,
            extract_type=template.extract_type,
            json_path=template.json_path,
            parser_code=template.parser_code
        )
        if template.header_group_id:
            async with async_session() as s:
                hres = await s.execute(select(HeaderGroupConfig).where(HeaderGroupConfig.id == template.header_group_id))
                hcfg = hres.scalar_one_or_none()
                if hcfg:
                    headers = dict(req.headers or {})
                    for k, v in (hcfg.headers or {}).items():
                        headers[k] = v
                    req.headers = headers
                    if hcfg.proxy_config_id:
                        pres = await s.execute(select(ProxyConfig).where(ProxyConfig.id == hcfg.proxy_config_id))
                        hproxy = pres.scalar_one_or_none()
                        if hproxy and hproxy.enabled:
                            purl = f"{hproxy.scheme}://{hproxy.ip}:{hproxy.port}"
                            req.proxies = {"http": purl, "https": purl}
        elif template.cookie_config_id:
            async with async_session() as s:
                cres = await s.execute(select(CookieConfig).where(CookieConfig.id == template.cookie_config_id))
                cookie = cres.scalar_one_or_none()
                if cookie:
                    headers = dict(req.headers or {})
                    headers["Cookie"] = cookie.cookie_text
                    req.headers = headers
                    if cookie.proxy_config_id:
                        pres = await s.execute(select(ProxyConfig).where(ProxyConfig.id == cookie.proxy_config_id))
                        cproxy = pres.scalar_one_or_none()
                        if cproxy and cproxy.enabled:
                            purl = f"{cproxy.scheme}://{cproxy.ip}:{cproxy.port}"
                            req.proxies = {"http": purl, "https": purl}
        return req
    
    async def save_history_from_template(self, template: BusinessTemplate, merged_params: dict[str, Any], scrape_request: ScrapeRequest, response: ScrapeResponse):
        async with async_session() as s:
            history = ScrapeHistory(
                template_id=template.id,
                template_name=template.name,
                url=template.url,
                method=template.method,
                request_params=merged_params,
                request_headers=scrape_request.headers,
                request_body=template.body_template,
                api_request_headers=None,
                api_request_params=merged_params,
                api_request_body={"template_name": template.name, "params": merged_params},
                success=response.success,
                response_data=response.data if response.success else None,
                raw_response=response.raw_response,
                error_message=response.error
            )
            s.add(history)
            await s.commit()
    
    async def scrape(self, request: ScrapeRequest) -> ScrapeResponse:
        """
        Execute a scrape request and return parsed data.
        
        Args:
            request: Scrape request configuration
        
        Returns:
            ScrapeResponse with success status and data
        """
        if not request.url:
            return ScrapeResponse(
                success=False,
                error="URL is required"
            )
        
        try:
            # Build client, supporting template-level proxy via transport if available
            transport = None
            if request.proxies:
                proxy_url = request.proxies.get("https") or request.proxies.get("http")
                if proxy_url:
                    try:
                        transport = httpx.AsyncHTTPTransport(proxy=proxy_url)
                    except Exception:
                        transport = None
            async with httpx.AsyncClient(timeout=30.0, trust_env=False, transport=transport) as client:
                if request.method == "GET":
                    response = await client.get(
                        request.url,
                        headers=request.headers or {},
                        params=request.params or {}
                    )
                else:  # POST
                    headers = request.headers or {}
                    # Detect Content-Type for form-urlencoded
                    content_type = ""
                    for k, v in headers.items():
                        if k.lower() == 'content-type':
                            content_type = v.lower()
                            break
                    
                    if 'application/x-www-form-urlencoded' in content_type:
                        # For form data, httpx uses data= parameter
                        # If body is a dict, it will be encoded; if string, sent as is
                        response = await client.post(
                            request.url,
                            headers=headers,
                            params=request.params or {},
                            data=request.body
                        )
                    else:
                        # Default to JSON
                        response = await client.post(
                            request.url,
                            headers=headers,
                            params=request.params or {},
                            json=request.body
                        )
                
                response.raise_for_status()
                raw_response = response.text
                
                # Try to parse as JSON
                try:
                    data = response.json()
                except Exception:
                    data = raw_response
                
                # Execute extraction based on type
                if request.extract_type == "jsonpath" and request.json_path:
                    parsed_data = extract_by_json_path(data, request.json_path)
                    return ScrapeResponse(
                        success=True,
                        data=parsed_data,
                        raw_response=data
                    )
                elif request.extract_type == "python" and request.parser_code:
                    try:
                        parsed_data = execute_parser(
                            request.parser_code,
                            data,
                            raw_response,
                            timeout=self.settings.parser_timeout
                        )
                        return ScrapeResponse(
                            success=True,
                            data=parsed_data,
                            raw_response=data
                        )
                    except ParserTimeoutError as e:
                        return ScrapeResponse(
                            success=False,
                            error=str(e),
                            raw_response=data
                        )
                    except ParserExecutionError as e:
                        return ScrapeResponse(
                            success=False,
                            error=str(e),
                            raw_response=data
                        )
                
                return ScrapeResponse(
                    success=True,
                    data=data,
                    raw_response=data
                )
                
        except httpx.HTTPStatusError as e:
            raw_text = None
            try:
                raw_text = e.response.text
            except Exception:
                raw_text = None
            return ScrapeResponse(
                success=False,
                error=f"HTTP error: {e.response.status_code} - {e.response.text}",
                raw_response=raw_text
            )
        except httpx.RequestError as e:
            return ScrapeResponse(
                success=False,
                error=f"Request error: {str(e)}"
            )
        except Exception as e:
            return ScrapeResponse(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )


# Singleton instance
scraper_service = ScraperService()
