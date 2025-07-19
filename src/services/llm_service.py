"""LLM service abstraction"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
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
                                           model: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """Generate structured response from LLM and return usage info"""
        pass

    @abstractmethod
    async def generate_text_response(self,
                                     messages: List[Dict[str, Any]],
                                     model: Optional[str] = None) -> Tuple[str, Dict[str, int]]:
        """Generate text response from LLM and return usage info"""
        pass


class OpenAILLMService(LLMService):
    """OpenAI implementation of LLM service using Responses API"""

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
                                           model: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """Generate structured response using OpenAI's Responses API with Structured Outputs"""
        try:
            # Convert messages to Responses API format
            input_messages = self._convert_messages_to_responses_format(
                messages)

            response = self.client.responses.create(
                model=model or self.settings.default_model,
                input=input_messages,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "structured_output",
                        "schema": schema,
                        "strict": True
                    }
                },
                max_output_tokens=self.settings.max_tokens
            )

            # Extract the structured result
            result = json.loads(response.output_text)

            # Extract usage information from Responses API
            usage_info = self._extract_usage_info(response)

            self.logger.debug(
                f"Generated structured response with {usage_info['total_tokens']} tokens")

            return result, usage_info

        except Exception as e:
            self.logger.error(f"LLM structured response failed: {e}")
            raise

    async def generate_text_response(self,
                                     messages: List[Dict[str, Any]],
                                     model: Optional[str] = None) -> Tuple[str, Dict[str, int]]:
        """Generate text response using OpenAI's Responses API"""
        try:
            # Convert messages to Responses API format
            input_messages = self._convert_messages_to_responses_format(
                messages)

            response = self.client.responses.create(
                model=model or self.settings.default_model,
                input=input_messages,
                max_output_tokens=self.settings.max_tokens
            )

            # Extract usage information
            usage_info = self._extract_usage_info(response)

            self.logger.debug(
                f"Generated text response with {usage_info['total_tokens']} tokens")

            return response.output_text, usage_info

        except Exception as e:
            self.logger.error(f"LLM text response failed: {e}")
            raise

    def _convert_messages_to_responses_format(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert standard messages format to Responses API format"""
        converted_messages = []

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            # Handle different content types
            if isinstance(content, str):
                converted_messages.append({
                    "role": role,
                    "content": content
                })
            elif isinstance(content, list):
                # Handle multimodal content (text + images, etc.)
                converted_messages.append({
                    "role": role,
                    "content": content
                })
            else:
                # Fallback to string conversion
                converted_messages.append({
                    "role": role,
                    "content": str(content)
                })

        return converted_messages

    def _extract_usage_info(self, response) -> Dict[str, int]:
        """Extract usage information from Responses API response"""
        try:
            # According to the Responses API documentation, usage info is available in response.usage
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage

                # Extract token counts
                input_tokens = getattr(usage, 'input_tokens', 0)
                output_tokens = getattr(usage, 'output_tokens', 0)
                total_tokens = getattr(usage, 'total_tokens', 0)

                # Handle reasoning tokens if present (for reasoning models)
                reasoning_tokens = 0
                if hasattr(usage, 'output_tokens_details') and usage.output_tokens_details:
                    reasoning_tokens = getattr(
                        usage.output_tokens_details, 'reasoning_tokens', 0)

                usage_info = {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "reasoning_tokens": reasoning_tokens
                }

                self.logger.debug(f"Extracted usage: {usage_info}")
                return usage_info
            else:
                self.logger.warning(
                    "No usage information available in response")
                return {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "reasoning_tokens": 0
                }
        except Exception as e:
            self.logger.error(f"Failed to extract usage info: {e}")
            return {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "reasoning_tokens": 0
            }
