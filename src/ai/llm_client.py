"""
Unified LLM client — supports Ollama (local) and OpenAI.
Privacy-first: defaults to local Ollama.
Includes retry logic, timeout handling, and response validation.
"""

import json
import time
from enum import Enum
from typing import Any, Optional

import httpx
import structlog
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.ai.prompts import PromptTemplate

logger = structlog.get_logger(__name__)


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"


class LLMResponse(BaseModel):
    content: str
    provider: LLMProvider
    model: str
    latency_ms: int
    parsed: Optional[dict[str, Any]] = None


class LLMConfig(BaseModel):
    provider: LLMProvider = LLMProvider.OLLAMA
    model: str = "llama3.2"
    fallback_model: str = "gpt-4o-mini"
    temperature: float = 0.1
    max_tokens: int = 1024
    timeout_seconds: int = 30
    ollama_base_url: str = "http://localhost:11434"
    openai_api_key: Optional[str] = None


class LLMClient:
    """
    Unified LLM client with automatic fallback.
    Primary: Ollama (local, private)
    Fallback: OpenAI (if configured)
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self._http = httpx.AsyncClient(timeout=config.timeout_seconds)
        logger.info(
            "LLM client initialized",
            provider=config.provider,
            model=config.model,
        )

    async def complete(
        self,
        prompt: PromptTemplate,
        variables: dict[str, Any],
        expect_json: bool = True,
    ) -> LLMResponse:
        """
        Complete a prompt with automatic JSON parsing.
        Tries primary provider, falls back automatically.
        """
        user_message = prompt.user_template.format(**variables)

        try:
            if self.config.provider == LLMProvider.OLLAMA:
                response = await self._ollama_complete(
                    system=prompt.system,
                    user=user_message,
                )
            else:
                response = await self._openai_complete(
                    system=prompt.system,
                    user=user_message,
                )

            if expect_json:
                response.parsed = self._parse_json(response.content)

            return response

        except Exception as e:
            logger.warning(
                "Primary LLM failed, attempting fallback",
                error=str(e),
                provider=self.config.provider,
            )
            return await self._fallback_complete(
                system=prompt.system,
                user=user_message,
                expect_json=expect_json,
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.TimeoutException),
    )
    async def _ollama_complete(self, system: str, user: str) -> LLMResponse:
        """Call local Ollama instance."""
        start = time.monotonic()

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        response = await self._http.post(
            f"{self.config.ollama_base_url}/api/chat",
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        content = data["message"]["content"]
        latency_ms = int((time.monotonic() - start) * 1000)

        logger.debug(
            "Ollama response",
            model=self.config.model,
            latency_ms=latency_ms,
        )

        return LLMResponse(
            content=content,
            provider=LLMProvider.OLLAMA,
            model=self.config.model,
            latency_ms=latency_ms,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.TimeoutException),
    )
    async def _openai_complete(self, system: str, user: str) -> LLMResponse:
        """Call OpenAI API."""
        if not self.config.openai_api_key:
            raise ValueError("OpenAI API key not configured")

        start = time.monotonic()

        headers = {
            "Authorization": f"Bearer {self.config.openai_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "response_format": {"type": "json_object"},
        }

        response = await self._http.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        latency_ms = int((time.monotonic() - start) * 1000)

        return LLMResponse(
            content=content,
            provider=LLMProvider.OPENAI,
            model=self.config.model,
            latency_ms=latency_ms,
        )

    async def _fallback_complete(
        self, system: str, user: str, expect_json: bool
    ) -> LLMResponse:
        """Attempt OpenAI fallback when primary fails."""
        if not self.config.openai_api_key:
            raise RuntimeError(
                "Primary LLM failed and no OpenAI fallback configured. "
                "Set OPENAI_API_KEY or ensure Ollama is running."
            )

        original_model = self.config.model
        self.config.model = self.config.fallback_model

        try:
            response = await self._openai_complete(system=system, user=user)
            if expect_json:
                response.parsed = self._parse_json(response.content)
            return response
        finally:
            self.config.model = original_model

    def _parse_json(self, content: str) -> dict[str, Any]:
        """
        Robustly parse JSON from LLM response.
        Handles markdown code blocks and extra text.
        """
        content = content.strip()

        # Strip markdown code blocks
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(
                line for line in lines
                if not line.startswith("```")
            ).strip()

        # Find JSON object boundaries
        start = content.find("{")
        end = content.rfind("}") + 1

        if start == -1 or end == 0:
            raise ValueError(f"No JSON found in LLM response: {content[:200]}")

        json_str = content[start:end]

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error("JSON parse failed", content=json_str[:200], error=str(e))
            raise ValueError(f"Invalid JSON from LLM: {e}") from e

    async def close(self) -> None:
        """Clean up HTTP client."""
        await self._http.aclose()

    async def __aenter__(self) -> "LLMClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()