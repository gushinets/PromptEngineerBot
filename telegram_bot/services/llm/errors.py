import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProviderErrorInfo:
    http_status: int
    provider_name: Optional[str] = None  
    code: Optional[str] = None           
    type: Optional[str] = None           
    message: Optional[str] = None        
    raw: Optional[str] = None            
    full_text: str = ""                  


def parse_error(http_status: int, body_text: str) -> ProviderErrorInfo:
    """
    Universal error parser for both OpenRouter and OpenAI-style responses.

    Supports:
    - OpenAI-ish: {"error": {"message": "...", "type": "...", "code": "..."}}
    - OpenRouter-ish: {"error": {"message": "...", "code": "...", "metadata": {"provider_name": "...", "raw": "...json..."}}}
      and extracts nested provider error fields from metadata.raw if present.
    """
    info = ProviderErrorInfo(http_status=http_status, full_text=body_text or "")

    try:
        top = json.loads(body_text or "")
    except Exception:
        return info

    err = top.get("error") if isinstance(top, dict) else None
    if not isinstance(err, dict):
        return info

    # Base layer (common for OpenAI + OpenRouter)
    msg = err.get("message")
    if isinstance(msg, str):
        info.message = msg

    code = err.get("code")
    if code is not None:
        info.code = str(code)

    etype = err.get("type")
    if isinstance(etype, str):
        info.type = etype

    # OpenRouter-specific metadata layer (optional)
    meta = err.get("metadata")
    if isinstance(meta, dict):
        provider_name = meta.get("provider_name")
        if isinstance(provider_name, str):
            info.provider_name = provider_name

        raw = meta.get("raw")
        if isinstance(raw, str):
            info.raw = raw


            try:
                raw_obj = json.loads(raw)
            except Exception:
                raw_obj = None

            if isinstance(raw_obj, dict):
                perr = raw_obj.get("error")
                if isinstance(perr, dict):
                    # Prefer nested provider fields if present
                    if isinstance(perr.get("code"), str):
                        info.code = perr["code"]
                    if isinstance(perr.get("type"), str):
                        info.type = perr["type"]
                    if isinstance(perr.get("message"), str):
                        info.message = perr["message"]

    return info



parse_openrouter_error = parse_error


class CountryRegionTerritoryNotSupportedError(Exception):
    """Raised when selected model does not support country/region/territory-specific features."""


class TranscriptionNotSupportedError(Exception):
    """Raised when selected model does not support audio transcription."""


class TranscriptionProviderNotSupportedError(Exception):
    """Raised when configured transcription provider is not supported by this client."""


class InternalServerError(Exception):
    """Raised when the LLM provider returns a 500 Internal Server Error."""
    
class IncorrectAPIKeyError(Exception):
    """Raised when the LLM provider returns a 401 Unauthorized error, indicating an incorrect API key."""