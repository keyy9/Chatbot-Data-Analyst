"""
LLM Client Module.

Handles all interactions with the Groq API (OpenAI-compatible chat
completions interface, served over Groq's fast inference).
Manages API calls, error handling, retry logic, and token counting.
"""

import asyncio
import logging
from typing import Optional, Dict, List
from datetime import datetime
import json

import httpx
from groq import Groq, AsyncGroq, RateLimitError, APIError
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from backend.ai.config import get_settings

# ============ Setup Logging ============
logger = logging.getLogger(__name__)


class LLMClientConfig:
    """
    Configuration for LLM client.

    Attributes:
        api_key: Groq API key
        model: Model name (e.g., "llama-3.3-70b-versatile", "llama-3.1-8b-instant")
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum tokens in response
        timeout: API request timeout in seconds
        max_retries: Maximum retry attempts for rate limits
        retry_delay: Initial delay for retries in seconds
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        settings = get_settings()

        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model
        self.temperature = temperature if temperature is not None else settings.groq_temperature
        self.max_tokens = max_tokens or settings.groq_max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def validate(self) -> bool:
        """
        Validate configuration.

        Returns:
            bool: True if valid.

        Raises:
            ValueError: If configuration is invalid.
        """
        if not self.api_key:
            raise ValueError("API key is required")

        if not self.model:
            raise ValueError("Model name is required")

        if self.temperature < 0 or self.temperature > 2:
            raise ValueError("Temperature must be between 0 and 2")

        if self.max_tokens < 1:
            raise ValueError("Max tokens must be at least 1")

        return True


class GeminiLLMClientConfig:
    """
    Configuration for the Gemini LLM client.

    Mirrors LLMClientConfig's shape, pulling gemini_* settings instead
    of groq_* ones, so GeminiLLMClient/AsyncGeminiLLMClient can be
    used interchangeably with LLMClient/AsyncLLMClient wherever an
    `llm_client` is injected.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        settings = get_settings()

        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        self.temperature = temperature if temperature is not None else settings.gemini_temperature
        self.max_tokens = max_tokens or settings.gemini_max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def validate(self) -> bool:
        """
        Validate configuration.

        Returns:
            bool: True if valid.

        Raises:
            ValueError: If configuration is invalid.
        """
        if not self.api_key:
            raise ValueError("Gemini API key is required (set GEMINI_API_KEY)")

        if not self.model:
            raise ValueError("Model name is required")

        if self.temperature < 0 or self.temperature > 2:
            raise ValueError("Temperature must be between 0 and 2")

        if self.max_tokens < 1:
            raise ValueError("Max tokens must be at least 1")

        return True


class TokenCounter:
    """
    Utility class for token counting and cost estimation.

    Uses approximate token counting (1 token ≈ 4 characters).
    For precise counting, use Groq's usage response fields directly.
    """

    # ============ Approximate Pricing (USD per 1K tokens) ============
    # These are rough estimates - verify current pricing at groq.com/pricing.
    PRICING_PER_MODEL = {
        "llama-3.3-70b-versatile": {
            "input": 0.00059,
            "output": 0.00079
        },
        "llama-3.1-8b-instant": {
            "input": 0.00005,
            "output": 0.00008
        },
        "gemma2-9b-it": {
            "input": 0.0002,
            "output": 0.0002
        }
    }

    # ============ Token Limits per Model (context window) ============
    TOKEN_LIMITS = {
        "llama-3.3-70b-versatile": 128_000,
        "llama-3.1-8b-instant": 128_000,
        "gemma2-9b-it": 8_192
    }

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count from text.

        Uses approximation: 1 token ≈ 4 characters.

        Args:
            text: The text to count tokens for.

        Returns:
            int: Estimated token count.
        """
        if not text:
            return 0

        # Rough approximation: 1 token per 4 characters
        # Add buffer for special tokens
        return max(1, len(text) // 4)

    @staticmethod
    def estimate_prompt_tokens(
        system_prompt: str,
        user_prompt: str,
        add_buffer: bool = True
    ) -> int:
        """
        Estimate tokens in a complete prompt.

        Args:
            system_prompt: The system prompt.
            user_prompt: The user prompt.
            add_buffer: Add 10% buffer for formatting tokens.

        Returns:
            int: Estimated token count.
        """
        system_tokens = TokenCounter.estimate_tokens(system_prompt)
        user_tokens = TokenCounter.estimate_tokens(user_prompt)

        total = system_tokens + user_tokens + 10  # +10 for message markers

        if add_buffer:
            total = int(total * 1.1)  # Add 10% buffer

        return total

    @staticmethod
    def estimate_cost(
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Estimate cost of API call.

        Args:
            model: Model name.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            float: Estimated cost in USD.
        """
        if model not in TokenCounter.PRICING_PER_MODEL:
            return 0.0

        pricing = TokenCounter.PRICING_PER_MODEL[model]
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]

        return input_cost + output_cost

    @staticmethod
    def get_token_limit(model: str) -> int:
        """
        Get token limit for a model.

        Args:
            model: Model name.

        Returns:
            int: Maximum token limit, or 8192 as default.
        """
        return TokenCounter.TOKEN_LIMITS.get(model, 8192)


class LLMResponse:
    """
    Structured response from LLM.

    Attributes:
        content: The response text
        model: Model used
        input_tokens: Tokens in input
        output_tokens: Tokens in output
        total_tokens: Total tokens used
        estimated_cost: Estimated cost in USD
        finish_reason: Why the generation finished (stop, length, etc.)
        timestamp: When the response was generated
        latency_ms: Response time in milliseconds
    """

    def __init__(
        self,
        content: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        finish_reason: str,
        latency_ms: float
    ):
        self.content = content
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = input_tokens + output_tokens
        self.finish_reason = finish_reason
        self.timestamp = datetime.utcnow()
        self.latency_ms = latency_ms

        # Calculate estimated cost
        self.estimated_cost = TokenCounter.estimate_cost(
            model,
            input_tokens,
            output_tokens
        )

    def to_dict(self) -> Dict:
        """
        Convert response to dictionary.

        Returns:
            Dict: Dictionary representation.
        """
        return {
            "content": self.content,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "finish_reason": self.finish_reason,
            "estimated_cost": self.estimated_cost,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp.isoformat()
        }


class LLMClient:
    """
    Synchronous LLM Client for the Groq API.

    Handles API calls, error handling, retry logic, and monitoring.
    """

    def __init__(self, config: Optional[LLMClientConfig] = None):
        """
        Initialize LLM Client.

        Args:
            config: LLMClientConfig instance. If None, uses default from settings.
        """
        self.config = config or LLMClientConfig()
        self.config.validate()

        self.client = Groq(api_key=self.config.api_key)
        logger.info(f"LLM Client initialized with model: {self.config.model}")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """
        Generate a response using the Groq API via LangChain (synchronous).
        """
        import time

        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        estimated_input_tokens = TokenCounter.estimate_prompt_tokens(system_prompt, user_prompt)
        start_time = time.time()

        logger.info(
            f"Calling Groq via LangChain: model={self.config.model}"
        )

        chat = ChatOpenAI(
            model=self.config.model,
            api_key=self.config.api_key,
            base_url="https://api.groq.com/openai/v1",
            temperature=temp,
            max_tokens=max_tok,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        from openai import RateLimitError as OpenAIRateLimitError, APIStatusError as OpenAIAPIStatusError
        
        response = None
        for attempt in range(5):
            try:
                response = chat.invoke(messages)
                break
            except (OpenAIRateLimitError, OpenAIAPIStatusError) as e:
                status_code = getattr(e, "status_code", None)
                is_rate_limit = isinstance(e, OpenAIRateLimitError) or status_code == 429
                is_temp_server = status_code == 503
                
                if (is_rate_limit or is_temp_server) and attempt < 4:
                    sleep_time = (2 ** attempt) * 5 + 2
                    logger.warning(
                        f"Temporary LLM error (status {status_code}). "
                        f"Retrying in {sleep_time}s... (Attempt {attempt + 1}/5)"
                    )
                    time.sleep(sleep_time)
                else:
                    raise

        if response is None:
            raise RuntimeError("Failed to generate response after retries")

        latency_ms = (time.time() - start_time) * 1000
        content = response.content
        token_usage = response.response_metadata.get("token_usage", {})
        input_tokens = token_usage.get("prompt_tokens", estimated_input_tokens)
        output_tokens = token_usage.get("completion_tokens", 0)
        finish_reason = response.response_metadata.get("finish_reason", "stop")

        logger.info(
            f"LangChain Groq call successful: "
            f"input_tokens={input_tokens}, output_tokens={output_tokens}, "
            f"latency={latency_ms:.0f}ms"
        )

        return LLMResponse(
            content=content,
            model=self.config.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=finish_reason,
            latency_ms=latency_ms
        )

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """
        Generate a JSON response from the Groq API.

        Attempts to parse response as JSON.

        Args:
            system_prompt: The system prompt.
            user_prompt: The user prompt.
            temperature: Optional override for temperature.
            max_tokens: Optional override for max tokens.

        Returns:
            Dict: Parsed JSON response.

        Raises:
            ValueError: If response is not valid JSON.
        """
        response = self.generate(system_prompt, user_prompt, temperature, max_tokens)

        try:
            # Try to parse JSON from response
            json_str = response.content

            # Clean up markdown JSON blocks if present
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            return json.loads(json_str.strip())

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {response.content}")
            raise ValueError(f"Response is not valid JSON: {str(e)}") from e

    def count_tokens(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> int:
        """
        Count tokens in prompts (estimation).

        Args:
            system_prompt: The system prompt.
            user_prompt: The user prompt.

        Returns:
            int: Estimated token count.
        """
        return TokenCounter.estimate_prompt_tokens(system_prompt, user_prompt)

    def estimate_cost(
        self,
        system_prompt: str,
        user_prompt: str,
        estimated_output_tokens: int = 500
    ) -> float:
        """
        Estimate cost for a prompt.

        Args:
            system_prompt: The system prompt.
            user_prompt: The user prompt.
            estimated_output_tokens: Expected output tokens (default: 500).

        Returns:
            float: Estimated cost in USD.
        """
        input_tokens = self.count_tokens(system_prompt, user_prompt)
        return TokenCounter.estimate_cost(self.config.model, input_tokens, estimated_output_tokens)


class AsyncLLMClient:
    """
    Asynchronous LLM Client for the Groq API.

    Handles async API calls, batching, and concurrent requests.
    """

    def __init__(self, config: Optional[LLMClientConfig] = None):
        """
        Initialize Async LLM Client.

        Args:
            config: LLMClientConfig instance.
        """
        self.config = config or LLMClientConfig()
        self.config.validate()

        self.client = AsyncGroq(api_key=self.config.api_key)
        logger.info(f"Async LLM Client initialized with model: {self.config.model}")

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """
        Generate a response using the Groq API via LangChain (asynchronous).
        """
        import time

        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        estimated_input_tokens = TokenCounter.estimate_prompt_tokens(system_prompt, user_prompt)
        start_time = time.time()

        logger.info(
            f"Calling Groq async via LangChain: model={self.config.model}"
        )

        chat = ChatOpenAI(
            model=self.config.model,
            api_key=self.config.api_key,
            base_url="https://api.groq.com/openai/v1",
            temperature=temp,
            max_tokens=max_tok,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        from openai import RateLimitError as OpenAIRateLimitError, APIStatusError as OpenAIAPIStatusError
        import asyncio
        
        response = None
        for attempt in range(5):
            try:
                response = await chat.ainvoke(messages)
                break
            except (OpenAIRateLimitError, OpenAIAPIStatusError) as e:
                status_code = getattr(e, "status_code", None)
                is_rate_limit = isinstance(e, OpenAIRateLimitError) or status_code == 429
                is_temp_server = status_code == 503
                
                if (is_rate_limit or is_temp_server) and attempt < 4:
                    sleep_time = (2 ** attempt) * 5 + 2
                    logger.warning(
                        f"Temporary LLM error (status {status_code}). "
                        f"Retrying in {sleep_time}s... (Attempt {attempt + 1}/5)"
                    )
                    await asyncio.sleep(sleep_time)
                else:
                    raise

        if response is None:
            raise RuntimeError("Failed to generate response after retries")

        latency_ms = (time.time() - start_time) * 1000
        content = response.content
        token_usage = response.response_metadata.get("token_usage", {})
        input_tokens = token_usage.get("prompt_tokens", estimated_input_tokens)
        output_tokens = token_usage.get("completion_tokens", 0)
        finish_reason = response.response_metadata.get("finish_reason", "stop")

        logger.info(
            f"Async LangChain Groq call successful: "
            f"input_tokens={input_tokens}, output_tokens={output_tokens}, "
            f"latency={latency_ms:.0f}ms"
        )

        return LLMResponse(
            content=content,
            model=self.config.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=finish_reason,
            latency_ms=latency_ms
        )

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """
        Generate a JSON response asynchronously.

        Args:
            system_prompt: The system prompt.
            user_prompt: The user prompt.
            temperature: Optional override for temperature.
            max_tokens: Optional override for max tokens.

        Returns:
            Dict: Parsed JSON response.
        """
        response = await self.generate(system_prompt, user_prompt, temperature, max_tokens)

        try:
            json_str = response.content

            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            return json.loads(json_str.strip())

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {response.content}")
            raise ValueError(f"Response is not valid JSON: {str(e)}") from e

    async def generate_batch(
        self,
        prompts: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_concurrent: int = 5
    ) -> List[LLMResponse]:
        """
        Generate responses for multiple prompts concurrently.

        Args:
            prompts: List of dicts with 'system' and 'user' keys.
            temperature: Optional override for temperature.
            max_tokens: Optional override for max tokens.
            max_concurrent: Maximum concurrent requests.

        Returns:
            List[LLMResponse]: List of responses in order.
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_with_semaphore(prompt_dict: Dict) -> LLMResponse:
            async with semaphore:
                return await self.generate(
                    system_prompt=prompt_dict["system"],
                    user_prompt=prompt_dict["user"],
                    temperature=temperature,
                    max_tokens=max_tokens
                )

        tasks = [generate_with_semaphore(prompt) for prompt in prompts]
        responses = await asyncio.gather(*tasks)

        return responses


GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"


def _parse_gemini_response(payload: Dict, model: str, latency_ms: float) -> LLMResponse:
    """Shared response parsing for the sync/async Gemini clients (OpenAI-compatible schema)."""
    choice = payload["choices"][0]
    usage = payload.get("usage", {})

    return LLMResponse(
        content=choice["message"]["content"],
        model=model,
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        finish_reason=choice.get("finish_reason", "stop"),
        latency_ms=latency_ms
    )


def _parse_gemini_json(response: LLMResponse) -> Dict:
    """Shared JSON-body parsing (markdown code fence stripping) for the Gemini clients."""
    json_str = response.content

    if "```json" in json_str:
        json_str = json_str.split("```json")[1].split("```")[0]
    elif "```" in json_str:
        json_str = json_str.split("```")[1].split("```")[0]

    try:
        return json.loads(json_str.strip())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from Gemini response: {response.content}")
        raise ValueError(f"Response is not valid JSON: {str(e)}") from e


class GeminiLLMClient:
    """
    Synchronous LLM client for Gemini (OpenAI-compatible chat completions
    gateway). Same public interface as LLMClient, so it's a drop-in
    replacement wherever an `llm_client` is injected.
    """

    def __init__(self, config: Optional[GeminiLLMClientConfig] = None):
        self.config = config or GeminiLLMClientConfig()
        self.config.validate()

        self.client = httpx.Client(
            base_url=GEMINI_BASE_URL,
            headers={
                "Authorization": f"Bearer {self.config.api_key}"
            }
        )
        logger.info(f"Gemini LLM Client initialized with model: {self.config.model}")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Generate a response using Gemini via LangChain (synchronous)."""
        import time

        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        estimated_input_tokens = TokenCounter.estimate_prompt_tokens(system_prompt, user_prompt)
        start_time = time.time()

        logger.info(
            f"Calling Gemini via LangChain: model={self.config.model}"
        )

        chat = ChatOpenAI(
            model=self.config.model,
            api_key=self.config.api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            temperature=temp,
            max_tokens=max_tok,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        from openai import RateLimitError as OpenAIRateLimitError, APIStatusError as OpenAIAPIStatusError
        
        response = None
        for attempt in range(5):
            try:
                response = chat.invoke(messages)
                break
            except (OpenAIRateLimitError, OpenAIAPIStatusError) as e:
                status_code = getattr(e, "status_code", None)
                is_rate_limit = isinstance(e, OpenAIRateLimitError) or status_code == 429
                is_temp_server = status_code == 503
                
                if (is_rate_limit or is_temp_server) and attempt < 4:
                    sleep_time = (2 ** attempt) * 5 + 2
                    logger.warning(
                        f"Temporary LLM error (status {status_code}). "
                        f"Retrying in {sleep_time}s... (Attempt {attempt + 1}/5)"
                    )
                    time.sleep(sleep_time)
                else:
                    raise

        if response is None:
            raise RuntimeError("Failed to generate response after retries")

        latency_ms = (time.time() - start_time) * 1000
        content = response.content
        token_usage = response.response_metadata.get("token_usage", {})
        input_tokens = token_usage.get("prompt_tokens", estimated_input_tokens)
        output_tokens = token_usage.get("completion_tokens", 0)
        finish_reason = response.response_metadata.get("finish_reason", "stop")

        logger.info(
            f"LangChain Gemini call successful: "
            f"input_tokens={input_tokens}, output_tokens={output_tokens}, "
            f"latency={latency_ms:.0f}ms"
        )

        return LLMResponse(
            content=content,
            model=self.config.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=finish_reason,
            latency_ms=latency_ms
        )

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """Generate a JSON response from Gemini. Mirrors LLMClient.generate_json()."""
        response = self.generate(system_prompt, user_prompt, temperature, max_tokens)
        return _parse_gemini_json(response)

    def count_tokens(self, system_prompt: str, user_prompt: str) -> int:
        """Count tokens in prompts (estimation). Mirrors LLMClient.count_tokens()."""
        return TokenCounter.estimate_prompt_tokens(system_prompt, user_prompt)

    def estimate_cost(
        self,
        system_prompt: str,
        user_prompt: str,
        estimated_output_tokens: int = 500
    ) -> float:
        """Estimate cost for a prompt. Mirrors LLMClient.estimate_cost() (returns 0.0 - Gemini pricing varies by routed model)."""
        input_tokens = self.count_tokens(system_prompt, user_prompt)
        return TokenCounter.estimate_cost(self.config.model, input_tokens, estimated_output_tokens)


class AsyncGeminiLLMClient:
    """
    Asynchronous LLM client for Gemini. Same public interface as
    AsyncLLMClient, so it's a drop-in replacement wherever an async
    `llm_client` is injected.
    """

    def __init__(self, config: Optional[GeminiLLMClientConfig] = None):
        self.config = config or GeminiLLMClientConfig()
        self.config.validate()

        self.client = httpx.AsyncClient(
            base_url=GEMINI_BASE_URL,
            headers={
                "Authorization": f"Bearer {self.config.api_key}"
            }
        )
        logger.info(f"Async Gemini LLM Client initialized with model: {self.config.model}")

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Generate a response using Gemini via LangChain (asynchronous)."""
        import time

        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        estimated_input_tokens = TokenCounter.estimate_prompt_tokens(system_prompt, user_prompt)
        start_time = time.time()

        logger.info(
            f"Calling Gemini async via LangChain: model={self.config.model}"
        )

        chat = ChatOpenAI(
            model=self.config.model,
            api_key=self.config.api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            temperature=temp,
            max_tokens=max_tok,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        from openai import RateLimitError as OpenAIRateLimitError, APIStatusError as OpenAIAPIStatusError
        import asyncio
        
        response = None
        for attempt in range(5):
            try:
                response = await chat.ainvoke(messages)
                break
            except (OpenAIRateLimitError, OpenAIAPIStatusError) as e:
                status_code = getattr(e, "status_code", None)
                is_rate_limit = isinstance(e, OpenAIRateLimitError) or status_code == 429
                is_temp_server = status_code == 503
                
                if (is_rate_limit or is_temp_server) and attempt < 4:
                    sleep_time = (2 ** attempt) * 5 + 2
                    logger.warning(
                        f"Temporary LLM error (status {status_code}). "
                        f"Retrying in {sleep_time}s... (Attempt {attempt + 1}/5)"
                    )
                    await asyncio.sleep(sleep_time)
                else:
                    raise

        if response is None:
            raise RuntimeError("Failed to generate response after retries")

        latency_ms = (time.time() - start_time) * 1000
        content = response.content
        token_usage = response.response_metadata.get("token_usage", {})
        input_tokens = token_usage.get("prompt_tokens", estimated_input_tokens)
        output_tokens = token_usage.get("completion_tokens", 0)
        finish_reason = response.response_metadata.get("finish_reason", "stop")

        logger.info(
            f"Async LangChain Gemini call successful: "
            f"input_tokens={input_tokens}, output_tokens={output_tokens}, "
            f"latency={latency_ms:.0f}ms"
        )

        return LLMResponse(
            content=content,
            model=self.config.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=finish_reason,
            latency_ms=latency_ms
        )

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """Generate a JSON response asynchronously. Mirrors AsyncLLMClient.generate_json()."""
        response = await self.generate(system_prompt, user_prompt, temperature, max_tokens)
        return _parse_gemini_json(response)


# ============ Singleton Instances (one per provider) ============
_sync_clients: Dict[str, object] = {}
_async_clients: Dict[str, object] = {}

SUPPORTED_LLM_PROVIDERS = ("groq", "gemini")


def get_llm_client(provider: str = "groq") -> LLMClient:
    """
    Get or create the global sync LLM client for the given provider.

    Args:
        provider: "groq" (default, preserves existing behavior) or "gemini".

    Returns:
        LLMClient or GeminiLLMClient: The client instance (duck-type compatible).
    """
    if provider not in SUPPORTED_LLM_PROVIDERS:
        raise ValueError(f"Unknown LLM provider: {provider!r}. Supported: {SUPPORTED_LLM_PROVIDERS}")

    if provider not in _sync_clients:
        _sync_clients[provider] = GeminiLLMClient() if provider == "gemini" else LLMClient()
    return _sync_clients[provider]


def get_async_llm_client(provider: str = "groq") -> AsyncLLMClient:
    """
    Get or create the global async LLM client for the given provider.

    Args:
        provider: "groq" (default, preserves existing behavior) or "gemini".

    Returns:
        AsyncLLMClient or AsyncGeminiLLMClient: The client instance (duck-type compatible).
    """
    if provider not in SUPPORTED_LLM_PROVIDERS:
        raise ValueError(f"Unknown LLM provider: {provider!r}. Supported: {SUPPORTED_LLM_PROVIDERS}")

    if provider not in _async_clients:
        _async_clients[provider] = AsyncGeminiLLMClient() if provider == "gemini" else AsyncLLMClient()
    return _async_clients[provider]
