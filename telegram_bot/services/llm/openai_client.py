import asyncio
import logging
from datetime import datetime

import openai
from openai import OpenAI, Timeout
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from telegram_bot.services.llm.base import LLMClientBase, TokenUsage
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import imageio_ffmpeg

from telegram_bot.services.llm.errors import (
    InternalServerError,
    CountryRegionTerritoryNotSupportedError,
    TranscriptionNotSupportedError,
    TranscriptionProviderNotSupportedError,
    parse_error,
    IncorrectAPIKeyError,
)


class OpenAIClient(LLMClientBase):
    """
    Client for interacting with the OpenAI API for chat completions.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str,
        max_retries: int = 5,
        request_timeout: float = 60.0,
        max_wait_time: float = 300.0,
        transcription_api_name: Optional[str] = None,
        transcription_model_name: Optional[str] = None,
    ):     
        """
        Initialize the OpenAI client.

        Args:
            api_key (str): OpenAI API key.
            model_name (str): Model name to use (e.g., 'gpt-4').
            max_retries (int): Maximum number of retry attempts.
            request_timeout (float): Timeout in seconds for each API request.
            max_wait_time (float): Maximum total time to wait for a response including retries.
        """
        super().__init__(api_key, model_name)
        self.max_retries = max_retries
        self.request_timeout = request_timeout
        self.max_wait_time = max_wait_time
        self.client = OpenAI(api_key=api_key)
        self.start_time = None
        

    def _log_retry(self, retry_state: RetryCallState) -> bool:
        """Log retry attempts and check max wait time."""
        if retry_state.attempt_number > 1:
            wait_time = retry_state.idle_for
            total_time = (datetime.now() - self.start_time).total_seconds()

            logging.warning(
                f"Retry attempt {retry_state.attempt_number} after {wait_time:.2f}s. "
                f"Total wait time: {total_time:.2f}s"
            )

            if total_time > self.max_wait_time:
                logging.error("Max wait time exceeded, giving up.")
                return False
        return True

    def _should_retry(self, retry_state):
        """Check if we should retry the request."""
        if retry_state.outcome.failed:
            return True  # Always retry on exception
        return self._log_retry(retry_state)

    @retry(
        stop=lambda retry_state: stop_after_attempt(retry_state.args[0].max_retries)(retry_state),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(
            (
                TimeoutError,
                ConnectionError,
                openai.APITimeoutError,
                openai.APIConnectionError,
            )
        ),
        before_sleep=lambda retry_state: logging.warning(
            f"Retrying (attempt {retry_state.attempt_number}): {retry_state.outcome.exception()}"
        )
        if retry_state.attempt_number > 1
        else None,
        retry_error_callback=lambda retry_state: logging.error(
            f"Max retries ({retry_state.attempt_number}) reached. Last error: {retry_state.outcome.exception()}"
        ),
    )
    async def _call_openai_api(
        self, messages: list[dict[str, str]], log_prefix: str = "[OpenAI]"
    ) -> tuple:
        """Make the actual API call with retry logic."""
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                timeout=Timeout(self.request_timeout),  # 60-second timeout
            ),
        )
        usage = getattr(response, "usage", None)
        token_usage = None
        if usage is not None:
            token_usage = TokenUsage(
                prompt_tokens=getattr(usage, "prompt_tokens", 0),
                completion_tokens=getattr(usage, "completion_tokens", 0),
                total_tokens=getattr(usage, "total_tokens", 0),
            )
        return response.choices[0].message.content, token_usage

    async def send_prompt(
        self, messages: list[dict[str, str]], log_prefix: str = "[OpenAI]"
    ) -> str:
        """
        Send a list of messages to the OpenAI chat completion API asynchronously.

        Args:
            messages: List of message dicts (role/content) for the conversation.
            log_prefix: Prefix for logging.

        Returns:
            The assistant's response from OpenAI.

        Raises:
            Exception: If the API request fails after all retry attempts.
        """
        logging.info(f"{log_prefix} Sending transcript to OpenAI: {messages}")
        self.start_time = datetime.now()

        try:
            response_text, usage = await self._call_openai_api(messages, log_prefix)
            self.last_usage = usage

            # Log token usage if available
            if usage:
                self.logger.info(
                    f"{log_prefix} Token usage - "
                    f"Prompt: {usage.prompt_tokens} tokens, "
                    f"Completion: {usage.completion_tokens} tokens, "
                    f"Total: {usage.total_tokens} tokens"
                )

            logging.info(f"{log_prefix} Received response from OpenAI: {response_text}")
            return response_text

        except Exception as e:
            total_time = (datetime.now() - self.start_time).total_seconds()
            logging.exception(
                f"{log_prefix} OpenAI API request failed after {total_time:.2f}s: {e!s}"
            )
            raise

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        audio_format: Optional[str] = "ogg",
        transcription_model: Optional[str] = None,
        log_prefix: str = "",
    ) -> str:
        self.logger.info("%s STT request: model=%s base_url=%s", log_prefix, transcription_model, getattr(self.client, "base_url", None))
        """
        Transcribe audio to text using OpenAI Audio Transcriptions API.
        Логика полностью как в OpenRouterClient.transcribe_audio:
        - пытаемся отправить как есть
        - если формат не подходит, вытаскиваем supported formats из ошибки
        - конвертируем ffmpeg в подходящий формат (приоритет: wav, потом mp3)
        - маппим типовые ошибки в ваши доменные исключения
        """

        model = transcription_model or self.model_name
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

            with tempfile.TemporaryDirectory(prefix="oa_transcribe_") as tmpdir:
                in_path = Path(tmpdir) / f"input.{source_format}"
                out_path = Path(tmpdir) / f"output.{target_format}"
                in_path.write_bytes(source_bytes)

                if target_format == "wav":
                    cmd = [
                        ffmpeg_path,
                        "-y",
                        "-loglevel", "error",
                        "-i", str(in_path),
                        "-ac", "1",
                        "-ar", "16000",
                        "-c:a", "pcm_s16le",
                        str(out_path),
                    ]
                else:
                    cmd = [
                        ffmpeg_path,
                        "-y",
                        "-loglevel", "error",
                        "-i", str(in_path),
                        "-ac", "1",
                        "-ar", "16000",
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

        def _map_openai_error(exc: Exception) -> tuple[int | None, str, str | None]:

            status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
            code = getattr(exc, "code", None)
            msg = str(exc)

            body = getattr(exc, "body", None)
            if isinstance(body, dict):
                err = body.get("error") or {}
                msg = err.get("message") or msg
                code = err.get("code") or code

            return status, msg, code

        async def _request_transcription(request_audio: bytes, request_format: str):
            with tempfile.TemporaryDirectory(prefix="oa_transcribe_req_") as tmpdir:
                p = Path(tmpdir) / f"audio.{request_format}"
                p.write_bytes(request_audio)

                def _sync_call():
                    with p.open("rb") as f:
                        resp = self.client.audio.transcriptions.create(
                            model=model,
                            file=f,
                            response_format="text",
                        )

                        text = getattr(resp, "text", None)
                        if text is None:
                            text = str(resp)
                        return ("" if text is None else str(text)).strip()

                try:
                    text = await asyncio.get_event_loop().run_in_executor(None, _sync_call)
                    if not text:
                        raise Exception("Transcription response contained empty/blank content")

                    self.logger.info(
                        "%s Transcription result (format=%s): %s",
                        log_prefix,
                        request_format,
                        text,
                    )
                    return True, text, 200, ""

                except Exception as e:
                    status, msg, code = _map_openai_error(e)
                    error_text = msg or str(e)

                    self.logger.error(
                        "%s Transcription failed: status=%s format=%s code=%s body=%s",
                        log_prefix,
                        status,
                        request_format,
                        code,
                        error_text,
                    )


                    return False, "", int(status) if status is not None else 0, error_text

        async def _do_request():
            tried: set[tuple[str, int]] = set()
            queue: list[tuple[bytes, str]] = [(audio_bytes, initial_format)]

            while queue:
                req_audio, req_format = queue.pop(0)
                key = (req_format, len(req_audio))
                if key in tried:
                    continue
                tried.add(key)

                ok, text, status, error_text = await _request_transcription(req_audio, req_format)
                if ok:
                    return text


                low = (error_text or "").lower()


                info = parse_error(status, error_text or "")


                if status in (400, 404) and (
                    (info.code and info.code in {"model_not_found", "invalid_model", "not_found"})
                    or (info.type and info.type in {"invalid_request_error"})
                    or (
                        info.message
                        and "model" in info.message.lower()
                        and ("not found" in info.message.lower() or "does not exist" in info.message.lower())
                    )
                ):
                    raise TranscriptionProviderNotSupportedError(f"Model '{model}' does not exist")

                
                if status in (400, 404) and (
                    (info.code and info.code in {"feature_not_supported", "not_supported"})
                    or (
                        info.message
                        and ("transcrib" in info.message.lower() or "audio/transcriptions" in info.message.lower())
                        and ("not supported" in info.message.lower() or "does not support" in info.message.lower())
                    )
                ):
                    raise TranscriptionNotSupportedError(
                        f"Model '{model}' does not support transcription on this endpoint"
                    )

                if status in (401, 403) and (
                    info.code and info.code in {'Incorrect API key', 'invalid_api_key', 'authentication_error', 'invalid_request_error'}
                ):
                    raise IncorrectAPIKeyError(
                        "Authentication with OpenAI API failed. Check your API key."
                        )
                
                if status == 403 and (
                    (info.code and info.code == "unsupported_country_region_territory")
                    or (info.message and "unsupported_country_region_territory" in info.message.lower())
                ):
                    raise CountryRegionTerritoryNotSupportedError(
                        f"Model '{model}' does not support transcription in the current country/region/territory"
                    )

                
                if status == 500 or status >= 500:
                    raise InternalServerError(
                        f"Model '{model}' returned Internal Server Error. This may be a temporary issue on the provider side."
                    )

                
                if status == 400:
                    fmt_source = info.full_text or info.message or ""
                    supported = _extract_supported_formats(fmt_source)
                    if supported and req_format not in supported:
                        self.logger.info(
                            "%s Model rejected format '%s'; supported formats: %s",
                            log_prefix,
                            req_format,
                            ", ".join(supported),
                        )

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

                raise Exception(f"Transcription failed: status={status} body={error_text}"
                            f"conversion from '{req_format}' to any supported format failed."
                        )

                raise Exception(f"Transcription failed: status={status} body={error_text}")

            raise Exception("Transcription failed: exhausted all format attempts")

        return await asyncio.wait_for(_do_request(), timeout=self.request_timeout)