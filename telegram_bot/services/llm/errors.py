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
    raw: Optional[str] = None  # raw json string from metadata.raw
    full_text: str = ""        # original body for fallback logging


def parse_openrouter_error(http_status: int, body_text: str) -> ProviderErrorInfo:
    info = ProviderErrorInfo(http_status=http_status, full_text=body_text)

    try:
        top = json.loads(body_text)
    except Exception:
        return info

    err = top.get("error") if isinstance(top, dict) else None
    if not isinstance(err, dict):
        return info

    info.message = err.get("message") if isinstance(err.get("message"), str) else info.message
    info.code = str(err.get("code")) if err.get("code") is not None else info.code

    meta = err.get("metadata")
    if isinstance(meta, dict):
        info.provider_name = meta.get("provider_name") if isinstance(meta.get("provider_name"), str) else None
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
                    if isinstance(perr.get("code"), str):
                        info.code = perr["code"]
                    if isinstance(perr.get("type"), str):
                        info.type = perr["type"]
                    if isinstance(perr.get("message"), str):
                        info.message = perr["message"]

    return info


class CountryRegionTerritoryNotSupportedError(Exception):
    """Raised when selected model does not support country/region/territory-specific features."""

class TranscriptionNotSupportedError(Exception):
    """Raised when selected model does not support audio transcription."""

class TranscriptionProviderNotSupportedError(Exception):
    """Raised when configured transcription provider is not supported by this client."""

class InternalServerError(Exception):
    """Raised when the LLM provider returns a 500 Internal Server Error."""
