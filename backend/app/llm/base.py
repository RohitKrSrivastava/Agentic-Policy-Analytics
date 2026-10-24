from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

class LLMResponse(BaseModel):
    content: str
    provider_name: str
    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    fallback_used: bool = False
    raw_response: Optional[Dict[str, Any]] = None

class BaseLLMProvider(ABC):
    def __init__(self, name: str, model_name: str, api_key: str = ""):
        self.name = name
        self.model_name = model_name
        self.api_key = api_key

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        max_tokens: int = 2000,
        temperature: float = 0.2
    ) -> LLMResponse:
        """
        Execute completion with the specified LLM provider.
        """
        pass

    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """
        Return status check (online, unconfigured, simulated, error) and latency.
        """
        pass
