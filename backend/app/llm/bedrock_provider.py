import time
import json
from typing import Optional, Dict, Any
from backend.app.llm.base import BaseLLMProvider, LLMResponse

class BedrockProvider(BaseLLMProvider):
    def __init__(self, access_key: str, secret_key: str, region: str = "ap-southeast-1", model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"):
        super().__init__(name="bedrock", model_name=model_id, api_key=access_key)
        self.secret_key = secret_key
        self.region = region

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        max_tokens: int = 2000,
        temperature: float = 0.2
    ) -> LLMResponse:
        if not self.api_key or not self.secret_key or self.api_key.startswith("AKIA-placeholder"):
            raise ValueError("AWS Bedrock credentials not provided or unconfigured.")

        # If boto3 is available and credentials are configured
        try:
            import boto3
            import botocore
            
            client = boto3.client(
                service_name="bedrock-runtime",
                region_name=self.region,
                aws_access_key_id=self.api_key,
                aws_secret_access_key=self.secret_key
            )
            
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            }
            if system_prompt:
                body["system"] = system_prompt

            start_time = time.time()
            response = client.invoke_model(
                modelId=self.model_name,
                body=json.dumps(body)
            )
            latency = (time.time() - start_time) * 1000.0
            response_body = json.loads(response["body"].read())
            
            content = ""
            for item in response_body.get("content", []):
                if item.get("type") == "text":
                    content += item.get("text", "")

            usage = response_body.get("usage", {})
            return LLMResponse(
                content=content,
                provider_name=self.name,
                model_name=self.model_name,
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
                total_tokens=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                latency_ms=round(latency, 2),
                fallback_used=False
            )
        except Exception as e:
            raise RuntimeError(f"AWS Bedrock Invocation Failed: {str(e)}")

    async def check_health(self) -> Dict[str, Any]:
        if not self.api_key or self.api_key.startswith("AKIA-placeholder"):
            return {
                "provider": self.name,
                "status": "unconfigured",
                "model": self.model_name,
                "latency_ms": 0.0,
                "message": "AWS Bedrock credentials not configured"
            }
        return {
            "provider": self.name,
            "status": "standby",
            "model": self.model_name,
            "latency_ms": 15.0
        }
