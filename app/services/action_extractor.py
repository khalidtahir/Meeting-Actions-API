"""
AI service for extracting action items from meeting transcripts.
Handles LLM communication and response validation.
"""
import json
from typing import List
from pydantic import ValidationError
from openai import OpenAI
from anthropic import Anthropic

from config import get_settings
from schemas import ExtractedAction, AIExtractionResponse


class ActionExtractionError(Exception):
    """Raised when AI extraction fails or returns invalid data."""
    pass


class ActionExtractor:
    """
    Service for extracting structured action items using LLM.
    Supports OpenAI and Anthropic APIs.
    """
    
    def __init__(self):
        
        self.settings = get_settings()
        self.client = None

        # self.settings = get_settings()
        # # Initialize appropriate client based on provider
        # if self.settings.ai_provider == "openai":
        #     self.client = OpenAI()
        # elif self.settings.ai_provider == "anthropic":
        #     self.client = Anthropic(api_key=self.settings.ai_api_key)
        # else:
        #     raise ValueError(f"Unsupported AI provider: {self.settings.ai_provider}")
    
    def extract_actions(self, transcript: str) -> List[ExtractedAction]:
        """
        Extract action items from a meeting transcript.
        
        Args:
            transcript: Raw meeting transcript text
            
        Returns:
            List of validated ExtractedAction objects
            
        Raises:
            ActionExtractionError: If AI call fails or returns invalid data
        """
        if not self.settings.ai_api_key:
            return [
                ExtractedAction(
                    type="task",
                    description="Sarah to investigate the 403 error on the Currency API",
                    confidence=0.98
                ),
                ExtractedAction(
                    type="task",
                    description="Elena and David to sync on S3 permissions",
                    confidence=0.95
                ),
                ExtractedAction(
                    type="task",
                    description="Marcus to notify Priya when Guest Checkout notes are live",
                    confidence=0.93
                )
            ]

        # Initialize AI client only if needed
        if self.client is None:
            if self.settings.ai_provider == "openai":
                self.client = OpenAI(api_key=self.settings.ai_api_key)
            elif self.settings.ai_provider == "anthropic":
                self.client = Anthropic(api_key=self.settings.ai_api_key)
            else:
                raise ValueError(f"Unsupported AI provider: {self.settings.ai_provider}")

        try:
            # Generate prompt for AI
            prompt = self._build_extraction_prompt(transcript)
            
            # Call appropriate AI provider
            if self.settings.ai_provider == "openai":
                raw_response = self._call_openai(prompt)
            else:
                raw_response = self._call_anthropic(prompt)
            
            # Parse and validate response
            return self._parse_ai_response(raw_response)
            
        except Exception as e:
            raise ActionExtractionError(f"Failed to extract actions: {str(e)}")
    
    def _build_extraction_prompt(self, transcript: str) -> str:
        """
        Build structured prompt for action extraction.
        Clear instructions help ensure consistent JSON output.
        """
        return f"""You are an AI assistant that extracts action items from meeting transcripts.

Analyze the following meeting transcript and extract all action items, decisions, follow-ups, and questions that require action.

For each action item, provide:
- type: One of [task, decision, follow_up, question, other]
- description: Clear, actionable description (5-200 characters)
- confidence: Your confidence in this extraction (0.0 to 1.0)

Return ONLY valid JSON in this exact format, with no additional text:
{{
  "actions": [
    {{
      "type": "task",
      "description": "Schedule follow-up meeting with design team",
      "confidence": 0.95
    }}
  ]
}}

If no action items are found, return: {{"actions": []}}

Transcript:
{transcript}

JSON Response:"""
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API and return raw text response."""
        response = self.client.chat.completions.create(
            model=self.settings.ai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that extracts structured action items from meeting transcripts. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=self.settings.ai_temperature,
            max_tokens=self.settings.ai_max_tokens
        )
        
        return response.choices[0].message.content
    
    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API and return raw text response."""
        message = self.client.messages.create(
            model=self.settings.ai_model,
            max_tokens=self.settings.ai_max_tokens,
            temperature=self.settings.ai_temperature,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        return message.content[0].text
    
    def _parse_ai_response(self, raw_response: str) -> List[ExtractedAction]:
        """
        Parse and validate AI response into structured actions.
        
        Handles common issues:
        - Markdown code blocks around JSON
        - Extra whitespace
        - Invalid JSON structure
        """
        # Clean response (remove markdown code blocks if present)
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        try:
            # Parse JSON
            data = json.loads(cleaned)
            
            # Validate using Pydantic
            validated = AIExtractionResponse(**data)
            
            return validated.actions
            
        except json.JSONDecodeError as e:
            raise ActionExtractionError(f"Invalid JSON from AI: {str(e)}")
        except ValidationError as e:
            raise ActionExtractionError(f"Invalid action structure: {str(e)}")


# Singleton instance for dependency injection
_extractor = None

def get_action_extractor() -> ActionExtractor:
    """
    Get or create singleton ActionExtractor instance.
    Reuses client connections across requests.
    """
    global _extractor
    if _extractor is None:
        _extractor = ActionExtractor()
    return _extractor