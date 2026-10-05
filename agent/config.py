from __future__ import annotations

import os

from dotenv import load_dotenv
from google import genai


load_dotenv()


DEFAULT_MODEL = "gemini-3.5-flash-lite"


class AgentConfigurationError(Exception):
    """Raised when the AI agent configuration is invalid."""


def get_gemini_api_key() -> str:
    """
    Read the Gemini API key from the environment.
    """

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise AgentConfigurationError(
            "GEMINI_API_KEY is not configured. "
            "Add it to the .env file."
        )

    return api_key


def get_model_name() -> str:
    """
    Return the configured Gemini model name.

    GEMINI_MODEL can override the default model.
    """

    model_name = os.getenv(
        "GEMINI_MODEL",
        DEFAULT_MODEL,
    ).strip()

    if not model_name:
        raise AgentConfigurationError(
            "GEMINI_MODEL cannot be empty."
        )

    return model_name


def create_gemini_client() -> genai.Client:
    """
    Create a configured Google GenAI client.
    """

    api_key = get_gemini_api_key()

    return genai.Client(
        api_key=api_key,
    )