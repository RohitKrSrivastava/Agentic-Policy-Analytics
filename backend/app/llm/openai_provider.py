import time
import json
import httpx
from typing import Optional, Dict, Any
from backend.app.llm.base import BaseLLMProvider, LLMResponse

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        super().__init__(name="openai", model_name=model_name, api_key=api_key)
        self.endpoint = "https://api.openai.com/v1/chat/completions"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        max_tokens: int = 2000,
        temperature: float = 0.2
    ) -> LLMResponse:
        if not self.api_key:
            raise ValueError("OpenAI API key not provided or unconfigured.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        start_time = time.time()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.endpoint, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"OpenAI API Error {resp.status_code}: {resp.text}")
            
            data = resp.json()
            latency = (time.time() - start_time) * 1000.0
            
            choice = data["choices"][0]
            content = choice["message"]["content"]
            usage = data.get("usage", {})

            return LLMResponse(
                content=content,
                provider_name=self.name,
                model_name=self.model_name,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                latency_ms=round(latency, 2),
                fallback_used=False,
                raw_response=data
            )

    async def check_health(self) -> Dict[str, Any]:
        if not self.api_key or self.api_key.startswith("sk-placeholder"):
            return {
                "provider": self.name,
                "status": "unconfigured",
                "model": self.model_name,
                "latency_ms": 0.0,
                "message": "API key not set in environment (fallback will engage)"
            }
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {self.api_key}"})
                latency = (time.time() - start) * 1000
                if res.status_code == 200:
                    return {"provider": self.name, "status": "active", "model": self.model_name, "latency_ms": round(latency, 2)}
                else:
                    return {"provider": self.name, "status": "error", "model": self.model_name, "latency_ms": round(latency, 2), "error": res.text}
        except Exception as e:
            return {"provider": self.name, "status": "error", "model": self.model_name, "latency_ms": round((time.time() - start) * 1000, 2), "error": str(e)}
