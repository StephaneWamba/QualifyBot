"""LLM service for conversation and data extraction."""

from openai import AsyncOpenAI

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class LLMService:
    """Service for OpenAI GPT-4o-mini operations."""

    def __init__(self):
        """Initialize OpenAI client."""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    async def generate_response(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate text response using GPT-4o-mini.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0-2)

        Returns:
            Generated text response
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )

            text = response.choices[0].message.content
            logger.debug("LLM response generated", prompt_length=len(
                prompt), response_length=len(text or ""))
            return text or ""

        except Exception as e:
            logger.error("LLM generation error",
                         error=str(e), prompt=prompt[:50])
            raise

    async def extract_structured_data(
        self,
        conversation_text: str,
        extraction_schema: dict,
    ) -> dict:
        """
        Extract structured data from conversation using GPT-4o-mini.

        Args:
            conversation_text: Conversation transcript
            extraction_schema: JSON schema for extraction

        Returns:
            Extracted data dictionary
        """
        try:
            system_prompt = f"""You are a data extraction assistant. Extract structured data from the conversation according to this schema:
{extraction_schema}

Return only valid JSON matching the schema."""

            prompt = f"Extract data from this conversation:\n\n{conversation_text}"

            response = await self.generate_response(prompt, system_prompt, temperature=0.3)

            # Parse JSON response
            import json
            data = json.loads(response)
            logger.info("Structured data extracted", fields=list(data.keys()))
            return data

        except Exception as e:
            logger.error("Data extraction error", error=str(e))
            raise

    async def summarize_conversation(self, conversation_text: str) -> str:
        """
        Summarize conversation using GPT-4o-mini.

        Args:
            conversation_text: Full conversation transcript

        Returns:
            Summary text
        """
        try:
            system_prompt = """You are a conversation summarizer. Create a concise summary of the conversation, highlighting key points and decisions."""

            prompt = f"Summarize this conversation:\n\n{conversation_text}"

            summary = await self.generate_response(prompt, system_prompt, temperature=0.5)
            logger.info("Conversation summarized", summary_length=len(summary))
            return summary

        except Exception as e:
            logger.error("Summarization error", error=str(e))
            raise


# Singleton instance
llm_service = LLMService()

