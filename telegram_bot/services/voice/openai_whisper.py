# telegram_bot/services/voice/openai_whisper.py

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
            with open(audio_path, "rb") as audio_file:
                form = aiohttp.FormData()
                form.add_field("file", audio_file, filename=os.path.basename(audio_path))
                form.add_field("model", self.model)
                form.add_field("language", lang)
                form.add_field("response_format", "text")
                
                async with session.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    data=form
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(f"Whisper API error {resp.status}: {error_text}")
                    return (await resp.text()).strip()