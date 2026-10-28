import logging

from backend.app.config import settings
from backend.app.llm.base import BaseLLMProvider, LLMResponse
from backend.app.llm.bedrock_provider import BedrockProvider
from backend.app.llm.gemini_provider import GeminiProvider
from backend.app.llm.local_fallback import LocalDeterministicFallbackProvider
from backend.app.llm.openai_provider import OpenAIProvider
from backend.app.models.schemas import ProviderHealth

logger = logging.getLogger("llm_router")

class MultiCloudLLMRouter:
    """
    Multi-Cloud LLM Router with automated failover and telemetry.
    Supports OpenAI, Google Cloud Gemini, AWS Bedrock, and an offline deterministic mode.
    """
    def __init__(self):
        self.providers: dict[str, BaseLLMProvider] = {
            "openai": OpenAIProvider(api_key=settings.OPENAI_API_KEY, model_name=settings.OPENAI_MODEL),
            "gemini": GeminiProvider(api_key=settings.GEMINI_API_KEY, model_name=settings.GEMINI_MODEL),
            "bedrock": BedrockProvider(
                access_key=settings.AWS_ACCESS_KEY_ID,
                secret_key=settings.AWS_SECRET_ACCESS_KEY,
                region=settings.AWS_REGION,
                model_id=settings.BEDROCK_MODEL_ID
            ),
            "local_fallback": LocalDeterministicFallbackProvider()
        }
        self.priority_order = settings.LLM_PROVIDER_PRIORITY

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        json_mode: bool = False,
        preferred_provider: str = "auto",
        max_tokens: int = 2000,
        temperature: float = 0.2
    ) -> tuple[LLMResponse, list[str]]:
        """
        Executes generation with automatic failover.
        Returns: (LLMResponse, list_of_attempted_providers)
        """
        attempted_providers: list[str] = []

        # Determine execution queue
        if preferred_provider != "auto" and preferred_provider in self.providers:
            # User specifically requested this provider first, then follow default fallback
            execution_order = [preferred_provider] + [p for p in self.priority_order if p != preferred_provider]
        else:
            execution_order = list(self.priority_order)

        last_error: Exception | None = None

        for provider_name in execution_order:
            provider = self.providers.get(provider_name)
            if not provider:
                continue

            attempted_providers.append(provider_name)
            try:
                logger.info(f"Attempting generation with provider: {provider_name} (Model: {provider.model_name})")
                response = await provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    json_mode=json_mode,
                    max_tokens=max_tokens,
                    temperature=temperature
                )

                # Mark whether fallback was required
                if len(attempted_providers) > 1:
                    response.fallback_used = True
                return response, attempted_providers

            except Exception as e:
                logger.warning(f"Provider '{provider_name}' failed: {e}. Cascading to next provider in fallback chain.")
                last_error = e
                continue

        # If all registered providers somehow failed, local fallback guarantee
        logger.error("All configured providers failed. Invoking hardwired safety fallback.")
        emergency_fallback = self.providers["local_fallback"]
        attempted_providers.append("local_fallback")
        res = await emergency_fallback.generate(prompt=prompt, system_prompt=system_prompt, json_mode=json_mode)
        res.fallback_used = True
        return res, attempted_providers

    def get_provider_for_preference(self, preferred_provider: str = "auto") -> BaseLLMProvider:
        if preferred_provider != "auto" and preferred_provider in self.providers:
            return self.providers[preferred_provider]
        for name in self.priority_order:
            p = self.providers.get(name)
            if p and getattr(p, "api_key", None):
                return p
        return self.providers["local_fallback"]

    async def get_providers_health(self) -> list[ProviderHealth]:
        health_list: list[ProviderHealth] = []
        for name, provider in self.providers.items():
            try:
                h = await provider.check_health()
                cost = 0.00015 if name == "openai" else (0.000075 if name == "gemini" else 0.003)
                if name == "local_fallback":
                    cost = 0.0
                health_list.append(ProviderHealth(
                    provider_name=name,
                    status=h.get("status", "unknown"),
                    latency_ms=h.get("latency_ms", 0.0),
                    model_name=provider.model_name,
                    cost_per_1k_tokens=cost,
                    is_fallback_available=True
                ))
            except Exception:
                health_list.append(ProviderHealth(
                    provider_name=name,
                    status="error",
                    latency_ms=0.0,
                    model_name=provider.model_name,
                    cost_per_1k_tokens=0.0,
                    is_fallback_available=True
                ))
        return health_list

llm_router = MultiCloudLLMRouter()
