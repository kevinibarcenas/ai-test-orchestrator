"""LLM service abstraction"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import json
from openai import OpenAI

from src.config.settings import Settings
from src.utils.logger import get_logger


class LLMService(ABC):
    """Abstract LLM service interface"""

    @abstractmethod
    async def generate_structured_response(self,
                                           messages: List[Dict[str, Any]],
                                           schema: Dict[str, Any],
                                           model: Optional[str] = None) -> Dict[str, Any]:
        """Generate structured response from LLM"""
        pass

    @abstractmethod
    async def generate_text_response(self,
                                     messages: List[Dict[str, Any]],
                                     model: Optional[str] = None) -> str:
        """Generate text response from LLM"""
        pass


class OpenAILLMService(LLMService):
    """OpenAI implementation of LLM service"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger("llm_service")
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout,
            max_retries=settings.openai_max_retries
        )

    async def generate_structured_response(self,
                                           messages: List[Dict[str, Any]],
                                           schema: Dict[str, Any],
                                           model: Optional[str] = None) -> Dict[str, Any]:
        """Generate structured response using OpenAI's Structured Outputs"""
        try:
            response = self.client.responses.create(
                model=model or self.settings.default_model,
                input=messages,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "structured_output",
                        "schema": schema,
                        "strict": True
                    }
                }
            )

            return json.loads(response.output_text)

        except Exception as e:
            self.logger.error(f"LLM structured response failed: {e}")
            raise

    async def generate_text_response(self,
                                     messages: List[Dict[str, Any]],
                                     model: Optional[str] = None) -> str:
        """Generate text response from OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=model or self.settings.default_model,
                messages=messages,
                max_tokens=self.settings.max_tokens
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"LLM text response failed: {e}")
            raise
