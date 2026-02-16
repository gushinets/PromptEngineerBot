# telegram_bot/services/voice/openai_whisper.py

import asyncio
from asyncio.log import logger
import os
import aiohttp
from .base import BaseVoiceService
from telegram_bot.utils.config import BotConfig

class OpenAIWhisperService(BaseVoiceService):
    def __init__(self, config: BotConfig):
        # openai_api_key — snake_case
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI Whisper service")
        self.api_key = config.openai_api_key  # snake_case
        
        # VOICE_LANGUAGE — UPPER_CASE
        self.language = config.VOICE_LANGUAGE or "ru"  # UPPER_CASE
        
        # WHISPER_MODEL — UPPER_CASE
        self.model = config.WHISPER_MODEL or "whisper-1"  # UPPER_CASE
    
    async def transcribe(self, audio_path: str, language: str = None) -> str:
        lang = language or self.language
        
        async with aiohttp.ClientSession() as session:
            try:
                with open(audio_path, "rb") as audio_file:
                    form = aiohttp.FormData()
                    form.add_field("file", audio_file, filename=os.path.basename(audio_path))
                    form.add_field("model", self.model)
                    form.add_field("language", lang)
                    form.add_field("response_format", "text")
                    
                    async with session.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        data=form,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status != 200:
                            error_text = await resp.text()
                            logger.error(
                                f" Whisper API ERROR | status={resp.status}, response={error_text[:200]}"
                            )
                            raise Exception(f"Whisper API error {resp.status}: {error_text}")
                        
                        result = (await resp.text()).strip()
                        logger.info(
                            f" Whisper API SUCCESS | file={os.path.basename(audio_path)}, "
                            f"chars={len(result)}, preview='{result[:50]}...'"
                        )
                        return result
                    
            except aiohttp.ClientConnectorError as e:
                logger.critical(
                    f" NETWORK ERROR: Cannot connect to OpenAI API. "
                    f"Is VPN enabled? Error: {e}",
                    exc_info=True
                )
                raise
            except asyncio.TimeoutError:
                logger.error(" Whisper API TIMEOUT (30s) - check network connection or VPN status")
                raise
            except Exception as e:
                logger.error(f" Unexpected error in Whisper API call: {e}", exc_info=True)
                raise