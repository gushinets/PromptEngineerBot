from .base import BaseVoiceService
from .openai_whisper import OpenAIWhisperService
from telegram_bot.utils.config import BotConfig

class VoiceServiceFactory:
    @staticmethod
    def create(config: BotConfig) -> BaseVoiceService:
        # VOICE_BACKEND — UPPER_CASE
        backend = config.VOICE_BACKEND.upper() if config.VOICE_BACKEND else "OPENAI_WHISPER"
        
        if backend == "OPENAI_WHISPER":
            return OpenAIWhisperService(config)
        else:
            raise ValueError(
                f"Unsupported voice backend: {backend}. "
                "Supported backends: OPENAI_WHISPER"
            )