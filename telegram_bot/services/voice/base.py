from abc import ABC, abstractmethod
from typing import Optional

class BaseVoiceService(ABC):
    @abstractmethod
    async def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        """Transcribe audio file to text"""
        pass
    