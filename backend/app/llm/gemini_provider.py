import time
import json
import httpx
from typing import Optional, Dict, Any
from backend.app.llm.base import BaseLLMProvider, LLMResponse

class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        super().__init__(name="gemini", model_name=model_name, api_key=api_key)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        max_tokens: int = 2000,
        temperature: float = 0.2
    ) -> LLMResponse:
        if not self.api_key:
            raise ValueError("Google Gemini API key not provided or unconfigured.")

        endpoint = f"{self.base_url}/{self.model_name}:generateContent?key={self.api_key}"
        
        contents = []
        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"SYSTEM INSTRUCTION: {system_prompt}\n\nPlease proceed accordingly."}]
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "Understood. I will strictly adhere to these instructions."}]
            })

        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        generation_config: Dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
        if json_mode:
            generation_config["responseMimeType"] = "application/json"

        payload = {
            "contents": contents,
            "generationConfig": generation_config
        }

        start_time = time.time()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(endpoint, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini API Error {resp.status_code}: {resp.text}")

            data = resp.json()
            latency = (time.time() - start_time) * 1000.0

            text_content = ""
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                text_content = "".join([p.get("text", "") for p in parts])

            usage_meta = data.get("usageMetadata", {})
            prompt_tokens = usage_meta.get("promptTokenCount", 0)
            completion_tokens = usage_meta.get("candidatesTokenCount", 0)

            return LLMResponse(
                content=text_content,
                provider_name=self.name,
                model_name=self.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                latency_ms=round(latency, 2),
                fallback_used=False,
                raw_response=data
            )

    async def check_health(self) -> Dict[str, Any]:
        if not self.api_key or self.api_key.startswith("AIzaSy-placeholder"):
            return {
                "provider": self.name,
                "status": "unconfigured",
                "model": self.model_name,
                "latency_ms": 0.0,
                "message": "Gemini API key not set in environment"
            }
        start = time.time()
        try:
            url = f"{self.base_url}/{self.model_name}?key={self.api_key}"
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url)
                latency = (time.time() - start) * 1000
                if res.status_code == 200:
                    return {"provider": self.name, "status": "active", "model": self.model_name, "latency_ms": round(latency, 2)}
                else:
                    return {"provider": self.name, "status": "error", "model": self.model_name, "latency_ms": round(latency, 2), "error": res.text}
        except Exception as e:
            return {"provider": self.name, "status": "error", "model": self.model_name, "latency_ms": round((time.time() - start) * 1000, 2), "error": str(e)}
