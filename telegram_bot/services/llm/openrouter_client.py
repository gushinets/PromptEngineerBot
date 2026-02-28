import re
import shutil
import subprocess
import tempfile
import asyncio
import logging
from typing import Optional
import aiohttp
import base64
from telegram_bot.services.llm.base import LLMClientBase, TokenUsage
from pathlib import Path
import imageio_ffmpeg
from telegram_bot.services.llm.errors import parse_openrouter_error, InternalServerError, CountryRegionTerritoryNotSupportedError, TranscriptionNotSupportedError, TranscriptionProviderNotSupportedError

class CountryRegionTerritoryNotSupportedError(Exception):
    """Raised when selected model does not support country/region/territory-specific features."""

class TranscriptionNotSupportedError(Exception):
    """Raised when selected model does not support audio transcription."""

class TranscriptionProviderNotSupportedError(Exception):
    """Raised when configured transcription provider is not supported by this client."""
    
class OpenRouterClient(LLMClientBase):
    """
    Client for interacting with the OpenRouter API for chat completions.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str,
        timeout: float = 60.0,
        transcription_api_name: str | None = None,
        transcription_model_name: str | None = None,
    ):
        """
        Initialize the OpenRouter client.
        Args:
            api_key (str): OpenRouter API key.
            model_name (str): Model name to use (e.g., 'openai/gpt-4').
            timeout (float): Request timeout in seconds.
        """
        super().__init__(api_key, model_name)
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.timeout = timeout
        self.transcription_api_key = transcription_api_name or api_key
        self.transcription_model_name = transcription_model_name or model_name
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/",  # Replace with your actual domain
            "Content-Type": "application/json",
        }

    async def send_prompt(self, messages: list[dict[str, str]], log_prefix: str = "") -> str:
        """
        Send messages to the OpenRouter chat completion API asynchronously.
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            log_prefix: Optional prefix for logging
        Returns:
            str: The assistant's response from OpenRouter.
        Raises:
            Exception: If the API request fails.
        """
        payload = {"model": self.model_name, "messages": messages}
        self.logger.info(f"{log_prefix} Sending transcript to model: {messages}")

        async with aiohttp.ClientSession() as session:

            async def _do_request():
                # Support both real session.post (async CM) and AsyncMock returning coroutine in tests
                post_result = session.post(self.base_url, headers=self.headers, json=payload)
                # If the result is an async context manager, use it; otherwise await it and wrap
                if hasattr(post_result, "__aenter__"):
                    response_cm = post_result
                else:
                    response_obj = await post_result

                    class _ResponseWrapper:
                        def __init__(self, resp):
                            self._resp = resp

                    async def __aenter__(self):
                        return self._resp

                    async def __aexit__(self, exc_type, exc, tb):
                        return False

                    response_cm = _ResponseWrapper(response_obj)

                async with response_cm as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logging.error(f"{log_prefix} API request failed: {error_text}")
                        raise Exception(f"API request failed: {error_text}")
                    data = await response.json()
                    response_text = data["choices"][0]["message"]["content"]

                    # Log token usage if available
                    if "usage" in data:
                        usage = data["usage"]
                        self.last_usage = TokenUsage(
                            prompt_tokens=usage.get("prompt_tokens", 0),
                            completion_tokens=usage.get("completion_tokens", 0),
                            total_tokens=usage.get("total_tokens", 0),
                        )
                        self.logger.info(
                            f"{log_prefix} Token usage - "
                            f"Prompt: {self.last_usage.prompt_tokens} tokens, "
                            f"Completion: {self.last_usage.completion_tokens} tokens, "
                            f"Total: {self.last_usage.total_tokens} tokens"
                        )

                    self.logger.info(f"{log_prefix} Received response from model: {response_text}")
                    return response_text

            try:
                return await asyncio.wait_for(_do_request(), timeout=self.timeout)
            except TimeoutError:
                self.logger.error(f"{log_prefix} Request timed out after {self.timeout} seconds")
                raise
    
    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        *,
        audio_format: Optional[str] = "ogg",
        transcription_model: Optional[str] = None,
        log_prefix: str = "",
        ) -> str:

        model = transcription_model or self.transcription_model_name
        initial_format = (audio_format or "ogg").lower().strip()

        def _extract_supported_formats(error_text: str) -> list[str]:
            self.logger.info(
                "%s Extracting supported audio formats from error message: %s",
                log_prefix,
                error_text,
            )
            m = re.search(r"Supported values are:\s*([^\n\r]+)", error_text)
            if not m:
                return []
            segment = m.group(1)
            formats = re.findall(r"'([a-zA-Z0-9]+)'", segment)
            out: list[str] = []
            for fmt in formats:
                f = fmt.lower().strip()
                if f and f not in out:
                    out.append(f)
            return out

        def _convert_audio_with_ffmpeg(
            source_bytes: bytes,
            source_format: str,
            target_format: str,
        ) -> bytes | None:
            self.logger.info(
                "%s Converting audio from %s to %s using ffmpeg",
                log_prefix,
                source_format,
                target_format,
            )
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

            with tempfile.TemporaryDirectory(prefix="or_transcribe_") as tmpdir:
                in_path = Path(tmpdir) / f"input.{source_format}"
                out_path = Path(tmpdir) / f"output.{target_format}"
                in_path.write_bytes(source_bytes)

                cmd = [
                    ffmpeg_path,
                    "-y",
                    "-loglevel",
                    "error",
                    "-i",
                    str(in_path),
                    str(out_path),
                ]
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                except subprocess.CalledProcessError as conv_err:
                    err = (conv_err.stderr or b"").decode("utf-8", errors="ignore")
                    self.logger.warning(
                        "%s ffmpeg conversion failed %s->%s: %s",
                        log_prefix,
                        source_format,
                        target_format,
                        err,
                    )
                    return None

                if not out_path.exists() or out_path.stat().st_size == 0:
                    self.logger.warning(
                        "%s ffmpeg produced empty output for %s->%s",
                        log_prefix,
                        source_format,
                        target_format,
                    )
                    return None

                return out_path.read_bytes()

        async def _request_transcription(
            session: aiohttp.ClientSession,
            request_audio: bytes,
            request_format: str,
        ):
            b64_audio = base64.b64encode(request_audio).decode("utf-8")
            payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                {"type": "text", "text": "Transcribe the audio exactly as spoken. Return only the transcription text.\n"
                    " Do not include any annotations, tags, or additional information.\n"
                    'If you cant transcribe the audio, respond with "Unable to transcribe".'},
                {"type": "input_audio", "input_audio": {"data": b64_audio, "format": request_format}}
                ]
            }]
            }

            transcription_headers = dict(self.headers)
            transcription_headers["Authorization"] = f"Bearer {self.transcription_api_key}"

            async with session.post(self.base_url, headers=transcription_headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    raw_content = data["choices"][0]["message"].get("content")
                    text = ("" if raw_content is None else str(raw_content)).strip()
                    if not text:
                        raise Exception("Transcription response contained empty/blank content")

                    self.logger.info(
                        "%s Transcription result (format=%s): %s",
                        log_prefix,
                        request_format,
                        text,
                    )
                    return True, text, 200, ""

                error_text = await response.text()
                self.logger.error(
                    "%s Transcription failed: status=%s format=%s body=%s",
                    log_prefix,
                    response.status,
                    request_format,
                    error_text,
                )
                return False, "", response.status, error_text

        async with aiohttp.ClientSession() as session:

            async def _do_request():
                tried: set[tuple[str, int]] = set()
                queue: list[tuple[bytes, str]] = [(audio_bytes, initial_format)]

                while queue:
                    req_audio, req_format = queue.pop(0)
                    key = (req_format, len(req_audio))
                    if key in tried:
                        continue
                    tried.add(key)

                    ok, text, status, error_text = await _request_transcription(session, req_audio, req_format)
                    if ok:
                        return text

                    info = parse_openrouter_error(status, error_text)
                    
                    if status == 404 and (info.message and "No endpoints found that support input audio" in info.message):
                        raise TranscriptionNotSupportedError(f"Model '{model}' does not support input audio")

                    if status == 403 and info.code == "unsupported_country_region_territory":
                        raise CountryRegionTerritoryNotSupportedError(f"Model '{model}' does not support transcription in the current country/region/territory")
                    
                    if status == 500 and info.code == 'Internal Server Error':
                        raise InternalServerError(f"Model '{model}' returned Internal Server Error. This may be a temporary issue on the provider side.")
                    
                    if status == 400:
                        supported = _extract_supported_formats(error_text)
                        if supported and req_format not in supported:
                            self.logger.info(
                                "%s Model rejected format '%s'; supported formats: %s",
                                log_prefix,
                                req_format,
                                ", ".join(supported),
                            )

                            # в приоритете wav, потом mp3
                            preferred_order = ["wav", "mp3"]
                            ordered = [f for f in preferred_order if f in supported] + [
                                f for f in supported if f not in preferred_order
                            ]

                            for target in ordered:
                                if target == req_format:
                                    continue
                                converted = _convert_audio_with_ffmpeg(req_audio, req_format, target)
                                if converted:
                                    queue.append((converted, target))
                                    break

                            if queue:
                                continue

                            raise Exception(
                                f"Transcription failed: provider accepts only {supported}, "
                                f"conversion from '{req_format}' to any supported format failed."
                            )

                    raise Exception(f"Transcription failed: status={status} body={error_text}")

            return await asyncio.wait_for(_do_request(), timeout=self.timeout)


                
            
                            
                    
                
                
