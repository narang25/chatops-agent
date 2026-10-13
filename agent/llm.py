"""
LLM Connection Module for ChatOps Agent.

Provides model initialization (Amazon Bedrock Converse / Ollama),
output sanitization (dropping reasoning tokens/<think> blocks),
and friendly error reporting for common AWS and connectivity issues.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import yaml
from dotenv import load_dotenv

# Try importing botocore exceptions for precise error handling
try:
    from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound
except ImportError:
    ClientError = None
    NoCredentialsError = None
    ProfileNotFound = None


def find_and_load_env() -> Path:
    """
    Locates and loads .env.agent using python-dotenv.
    Searches current working directory and parent directories.
    Credentials come strictly from environment variables, never hardcoded.
    """
    current_dir = Path.cwd()
    search_paths = [
        current_dir / ".env.agent",
        current_dir.parent / ".env.agent",
        Path(__file__).resolve().parent.parent / ".env.agent",
        Path(__file__).resolve().parent / ".env.agent",
    ]

    for env_file in search_paths:
        if env_file.exists():
            load_dotenv(dotenv_path=env_file)
            return env_file

    # Fallback to default load_dotenv() search
    load_dotenv()
    return current_dir / ".env.agent"


def load_config(config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Reads LLM settings from agent/config.yaml.
    """
    if config_path is None:
        # Default to agent/config.yaml relative to this file
        config_path = Path(__file__).resolve().parent / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    return config


def clean_env_vars() -> None:
    """
    Cleans up empty-string AWS environment variables.
    In boto3, setting AWS_PROFILE="" causes ProfileNotFound errors.
    """
    for key in ["AWS_PROFILE", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"]:
        if os.environ.get(key) == "":
            del os.environ[key]


def handle_llm_error(error: Exception) -> str:
    """
    Translates low-level exceptions into clear, friendly error messages
    suitable for debugging and viva explanations.
    """
    error_msg = str(error)

    # Botocore ClientError (Bedrock)
    if ClientError and isinstance(error, ClientError):
        code = error.response.get("Error", {}).get("Code", "")
        message = error.response.get("Error", {}).get("Message", error_msg)

        if "AccessDenied" in code or "AccessDeniedException" in code or "403" in code or "not allowed by policy" in message:
            return (
                f"[AccessDeniedException / 403 Forbidden]\n"
                f"Cause: Model access is not enabled or IAM/API key policy does not allow this action.\n"
                f"Details: {message}\n"
                f"Fix: Check your Bedrock model access in the AWS console, verify your AWS permissions, "
                f"or ensure the configured Bedrock API key has permission for this model."
            )

        if "ValidationException" in code or "400" in code:
            return (
                f"[ValidationException / 400 Bad Request]\n"
                f"Cause: Invalid model ID or model requires a cross-region inference profile.\n"
                f"Details: {message}\n"
                f"Fix: Verify the model ID with `python agent/scripts/list_models.py`. "
                f"For many models (including Claude or Qwen), use the regional inference profile prefix, e.g. 'us.<model_id>'."
            )

        if "ThrottlingException" in code or "TooManyRequests" in code or "429" in code:
            return (
                f"[ThrottlingException / 429 Too Many Requests]\n"
                f"Cause: Bedrock API request rate limit exceeded.\n"
                f"Details: {message}\n"
                f"Fix: Wait a few seconds before retrying or request a quota increase in AWS Service Quotas."
            )

    # Missing credentials
    if (NoCredentialsError and isinstance(error, NoCredentialsError)) or "Unable to locate credentials" in error_msg:
        return (
            f"[Missing Credentials]\n"
            f"Cause: No valid AWS credentials found in environment.\n"
            f"Fix: Fill in AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY or AWS_BEARER_TOKEN_BEDROCK in .env.agent."
        )

    # Ollama connection failure
    if "Connection refused" in error_msg or "Failed to connect to" in error_msg:
        return (
            f"[Connection Error]\n"
            f"Cause: Unable to connect to LLM server ({error_msg}).\n"
            f"Fix: If using Ollama, ensure the Ollama daemon is running with `ollama serve` and the model is pulled."
        )

    return f"[LLM Error: {type(error).__name__}] {error_msg}"


def clean_output(message: Any) -> str:
    """
    Extracts only the final answer text from an LLM response.

    Rules:
    1. If content is a list of blocks, keeps only text blocks and drops reasoning blocks.
    2. Strips any <think>...</think> sections (including unclosed thinking tags).
    3. Raw reasoning must never reach the user.
    """
    # Extract raw content
    if isinstance(message, str):
        content = message
    elif hasattr(message, "content"):
        content = message.content
    else:
        content = str(message)

    # Handle structured content blocks (e.g. Bedrock Converse or multi-part messages)
    if isinstance(content, list):
        text_parts: List[str] = []
        for block in content:
            if isinstance(block, str):
                text_parts.append(block)
            elif isinstance(block, dict):
                # Identify reasoning vs text blocks
                block_type = block.get("type", "")
                if block_type in ("reasoning", "reasoning_content", "thinking"):
                    continue
                if "reasoning_content" in block:
                    continue
                if "text" in block:
                    text_parts.append(str(block["text"]))
                elif block_type == "text":
                    text_parts.append(str(block.get("text", "")))
            elif hasattr(block, "text"):
                text_parts.append(str(block.text))
        extracted_text = "".join(text_parts)
    else:
        extracted_text = str(content)

    # Strip <think>...</think> tags
    cleaned = re.sub(r"<think>.*?</think>", "", extracted_text, flags=re.DOTALL)
    # Strip any dangling/unclosed <think> tag till end of text
    cleaned = re.sub(r"<think>.*$", "", cleaned, flags=re.DOTALL)

    return cleaned.strip()


def get_llm(config_path: Optional[Union[str, Path]] = None) -> Any:
    """
    Reads agent/config.yaml and returns an initialized Chat model:
    - ChatBedrockConverse (from langchain-aws) if provider is 'bedrock'
    - ChatOllama (from langchain-ollama) if provider is 'ollama'

    Credentials come exclusively from environment variables (.env.agent).
    """
    find_and_load_env()
    clean_env_vars()
    config = load_config(config_path)

    provider = config.get("provider", "bedrock").lower()
    temperature = float(config.get("temperature", 0))
    max_tokens = int(config.get("max_tokens", 2048))

    if provider == "bedrock":
        try:
            from langchain_aws import ChatBedrockConverse
        except ImportError as e:
            raise ImportError(
                "langchain-aws is required for Bedrock. Install with `pip install langchain-aws`."
            ) from e

        bedrock_cfg = config.get("bedrock", {})
        model_id = bedrock_cfg.get("model_id", "qwen.qwen3-235b-a22b-2507-v1:0")
        region = os.getenv("AWS_REGION", bedrock_cfg.get("region", "us-east-1"))

        # Check for bearer token / Bedrock API key
        bearer_token = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
        profile = os.getenv("AWS_PROFILE")

        kwargs: Dict[str, Any] = {
            "model_id": model_id,
            "region_name": region,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if bearer_token:
            kwargs["bedrock_api_key"] = bearer_token
        elif profile:
            kwargs["credentials_profile_name"] = profile

        return ChatBedrockConverse(**kwargs)

    elif provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError as e:
            raise ImportError(
                "langchain-ollama is required for Ollama. Install with `pip install langchain-ollama`."
            ) from e

        ollama_cfg = config.get("ollama", {})
        model = ollama_cfg.get("model", "llama3.2:1b")
        base_url = os.getenv("OLLAMA_BASE_URL", ollama_cfg.get("base_url", "http://localhost:11434"))

        return ChatOllama(
            model=model,
            base_url=base_url,
            temperature=temperature,
        )

    else:
        raise ValueError(
            f"Unsupported LLM provider '{provider}' in config. Allowed values are 'bedrock' or 'ollama'."
        )
