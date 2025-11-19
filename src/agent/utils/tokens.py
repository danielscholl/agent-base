"""Token counting utilities for context tracking and cost optimization.

Provides accurate token counting for LLM context management using tiktoken.
Falls back to word-based estimation when tiktoken is unavailable.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Cache encoding to avoid repeated loading
_encoding_cache: dict[str, Any] = {}

# Approximate tokens-per-word ratio for English text (fallback when tiktoken is unavailable).
# Value based on OpenAI's published guidance and tiktoken documentation:
# https://platform.openai.com/tokenizer, https://github.com/openai/tiktoken
# Typical accuracy: ±20% for standard English prose; may vary significantly for other languages,
# code, or highly technical domains. Use only as a rough estimate.
TOKENS_PER_WORD_ESTIMATE = 1.3


def count_tokens(text: str, encoding: str = "cl100k_base") -> int:
    """Count tokens in text using tiktoken encoding.

    Uses cl100k_base encoding by default, which is accurate for:
    - GPT-4, GPT-4-turbo
    - GPT-3.5-turbo
    - Claude models (good approximation)
    - Most modern LLMs

    Args:
        text: Text to count tokens for
        encoding: Tiktoken encoding name (default: cl100k_base)

    Returns:
        Number of tokens in text

    Example:
        >>> count_tokens("Hello world!")
        3
        >>> count_tokens("This is a longer sentence with more tokens.")
        9
    """
    if not text:
        return 0

    try:
        import tiktoken

        # Use cached encoding if available
        if encoding not in _encoding_cache:
            _encoding_cache[encoding] = tiktoken.get_encoding(encoding)

        enc = _encoding_cache[encoding]
        return len(enc.encode(text))

    except ImportError:
        # tiktoken not available (not in regular deps, only dev)
        # Use word count estimation: ~1.3 tokens per word for English
        return _estimate_tokens_from_words(text)

    except Exception as e:
        logger.warning(f"Token counting failed: {e}, using word estimation")
        return _estimate_tokens_from_words(text)


def count_tokens_for_model(text: str, model: str) -> int:
    """Count tokens for a specific model using its native encoding.

    Automatically selects the correct encoding for the model.
    More accurate than using a generic encoding.

    Args:
        text: Text to count tokens for
        model: Model name (e.g., "gpt-4", "gpt-3.5-turbo", "claude-sonnet-4-5")

    Returns:
        Number of tokens in text

    Example:
        >>> count_tokens_for_model("Hello world!", "gpt-4")
        3
    """
    if not text:
        return 0

    try:
        import tiktoken

        # Map model names to encodings
        # Most modern models use cl100k_base
        model_lower = model.lower()

        if "gpt-4" in model_lower or "gpt-3.5" in model_lower:
            # Use tiktoken's model-specific encoding, fallback to cl100k_base if unknown
            try:
                enc = tiktoken.encoding_for_model(model)
            except Exception:
                logger.warning(f"Unknown model '{model}' for tiktoken, using cl100k_base encoding")
                enc = tiktoken.get_encoding("cl100k_base")
        elif "claude" in model_lower:
            # Claude uses similar tokenization to GPT-4
            enc = tiktoken.get_encoding("cl100k_base")
        elif "gemini" in model_lower:
            # Gemini approximation (no official tokenizer in tiktoken)
            enc = tiktoken.get_encoding("cl100k_base")
        else:
            # Default to cl100k_base for unknown models
            enc = tiktoken.get_encoding("cl100k_base")

        return len(enc.encode(text))

    except ImportError:
        return _estimate_tokens_from_words(text)

    except Exception as e:
        logger.warning(f"Token counting for {model} failed: {e}, using estimation")
        return _estimate_tokens_from_words(text)


def _estimate_tokens_from_words(text: str) -> int:
    """Estimate token count from word count.

    Uses 1.3 tokens per word ratio, which is typical for English text.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    word_count = len(text.split())
    return int(word_count * TOKENS_PER_WORD_ESTIMATE)


def format_token_count(count: int) -> str:
    """Format token count for display.

    Args:
        count: Token count

    Returns:
        Formatted string (e.g., "1.2k", "500")

    Example:
        >>> format_token_count(500)
        '500'
        >>> format_token_count(1500)
        '1.5k'
        >>> format_token_count(1000000)
        '1.0M'
    """
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}k"
    else:
        return str(count)
