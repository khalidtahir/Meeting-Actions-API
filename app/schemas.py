"""
Pydantic schemas for request/response validation.
These define the API contract and handle serialization.
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List
from models import MeetingStatus


# ============= Request Schemas =============

class MeetingCreate(BaseModel):
    """Request body for creating a new meeting."""
    title: str = Field(..., min_length=1, max_length=200, description="Meeting title")
    transcript: str = Field(..., min_length=10, description="Meeting transcript text")


# ============= Response Schemas =============

class ActionResponse(BaseModel):
    """
    Response schema for a single action item.
    Validates confidence is in valid range.
    """
    id: str
    meeting_id: str
    type: str
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    class Config:
        from_attributes = True  # Allows conversion from ORM models


class MeetingResponse(BaseModel):
    """
    Response schema for meeting metadata.
    Excludes large transcript field by default.
    """
    id: str
    title: str
    status: MeetingStatus
    created_at: datetime
    
    class Config:
        from_attributes = True


class MeetingDetailResponse(MeetingResponse):
    """
    Extended meeting response that includes the transcript.
    Use sparingly since transcripts can be large.
    """
    transcript: str


class MeetingActionsResponse(BaseModel):
    """
    Response for getting all actions from a meeting.
    Groups metadata with actions list.
    """
    meeting_id: str
    meeting_title: str
    status: MeetingStatus
    actions: List[ActionResponse]


# ============= Internal AI Schemas =============

class ExtractedAction(BaseModel):
    """
    Schema for action items extracted by AI.
    Used to validate AI response before saving to DB.
    """
    type: str = Field(..., description="Action type: task, decision, follow_up, etc.")
    description: str = Field(..., min_length=5, description="Clear action description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence score")
    
    @field_validator('type')
    def validate_type(cls, v):
        """Ensure type is one of expected values."""
        allowed_types = {'task', 'decision', 'follow_up', 'question', 'other'}
        if v.lower() not in allowed_types:
            # Allow it but could log a warning
            pass
        return v.lower()


class AIExtractionResponse(BaseModel):
    """
    Expected structure from AI API.
    Validates entire response before processing.
    """
    actions: List[ExtractedAction]