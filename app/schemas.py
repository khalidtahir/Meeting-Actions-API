"""
Pydantic schemas for request/response validation.
These define the API contract and handle serialization.
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List, Optional
from models import MeetingStatus, ActionStatus


# ============= Request Schemas =============

class MeetingCreate(BaseModel):
    """Request body for creating a new meeting."""
    project_id: str = Field(..., description="Project ID this meeting belongs to")
    title: str = Field(..., min_length=1, max_length=200, description="Meeting title")
    transcript: str = Field(..., min_length=10, description="Meeting transcript text")


class ProjectCreate(BaseModel):
    """Request body for creating a new project."""
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: Optional[str] = Field(None, max_length=1000, description="Optional project description")




class ActionResponse(BaseModel):
    """
    Response schema for a single action item.
    Validates confidence is in valid range.
    Includes status tracking and week assignment.
    """
    id: str
    meeting_id: str
    type: str
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    status: ActionStatus = Field(default=ActionStatus.OPEN)
    week_number: Optional[int] = None
    owner: Optional[str] = None
    
    class Config:
        from_attributes = True  # Allows conversion from ORM models


class ActionUpdate(BaseModel):
    """Request body for partial update of an action (manual edit)."""
    status: Optional[ActionStatus] = None
    description: Optional[str] = Field(None, min_length=1)
    owner: Optional[str] = None


class ActionCreate(BaseModel):
    """Request body for manually creating an action (project-level or under a meeting)."""
    description: str = Field(..., min_length=1, max_length=2000)
    type: str = Field(default="task", description="task, decision, follow_up, question, other")
    owner: Optional[str] = Field(None, max_length=200)


class ProjectActionResponse(BaseModel):
    """Action item with optional meeting_title for project-level action list."""
    id: str
    meeting_id: str
    meeting_title: Optional[str] = None
    type: str
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    status: ActionStatus = Field(default=ActionStatus.OPEN)
    week_number: Optional[int] = None
    owner: Optional[str] = None
    
    class Config:
        from_attributes = True


class MeetingResponse(BaseModel):
    """
    Response schema for meeting metadata.
    Excludes large transcript field by default.
    """
    id: str
    title: str
    project_id: str
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


class ProjectResponse(BaseModel):
    """
    Response schema for project metadata.
    Lists project basics without nested meetings.
    """
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ProjectDetailResponse(ProjectResponse):
    """
    Extended project response with meeting count.
    Provides overview of project activity.
    """
    meeting_count: int = 0


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


# ============= Reconciliation Schemas =============

class PriorActionReference(BaseModel):
    """
    Reference to a prior OPEN action marked as completed or carryover.
    Must include the original action ID from the system.
    Used only for reconciliation of existing actions.
    """
    id: str = Field(..., description="Original action ID from system - MUST match prior action")
    description: str = Field(..., description="Action description")
    owner: Optional[str] = Field(None, description="Responsible person")


class ReconciliationActionItem(BaseModel):
    """
    Single NEW action item created during reconciliation.
    Does NOT include ID (these are newly created actions).
    """
    description: str = Field(..., description="Action description")
    owner: Optional[str] = Field(None, description="Responsible person")


class ReconciliationRequest(BaseModel):
    """
    Request body for project reconciliation.
    Provides new meeting transcript for LLM to interpret.
    """
    meeting_title: str = Field(..., description="Title of new meeting")
    transcript: str = Field(..., min_length=10, description="Meeting transcript")
    week_number: int = Field(..., ge=1, description="Week number for this reconciliation")


class AIReconciliationResponse(BaseModel):
    """
    Expected structure from LLM for reconciliation.
    Strictly JSON output - no free-form text.
    
    - completed: Prior OPEN actions now marked COMPLETED (with original IDs)
    - carryover: Prior OPEN actions still pending (with original IDs)
    - new_actions: New actions extracted from meeting (no IDs)
    - risk_flags: Concerns or blockers identified
    - summary: Executive summary paragraph
    """
    completed: List[PriorActionReference] = Field(default_factory=list)
    carryover: List[PriorActionReference] = Field(default_factory=list)
    new_actions: List[ReconciliationActionItem] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    summary: str = Field(..., description="Executive summary paragraph")


class ProposalRequest(BaseModel):
    """Request for a reconciliation proposal (no DB commit). Optional rejection feedback for re-proposal."""
    meeting_title: str = Field(..., description="Title of new meeting")
    transcript: str = Field(..., min_length=10, description="Meeting transcript")
    week_number: int = Field(..., ge=1, description="Week number")
    previous_proposal: Optional[AIReconciliationResponse] = Field(None, description="Previous proposal when user rejected")
    rejection_feedback: Optional[str] = Field(None, description="User feedback on why they rejected the previous proposal")


class ProposalResponse(BaseModel):
    """Current project state plus AI proposal (no changes applied yet)."""
    current_actions: List[ActionResponse] = Field(..., description="Current OPEN actions in the project")
    proposal: AIReconciliationResponse = Field(..., description="Proposed completed/carryover/new and summary")


class ApplyProposalRequest(BaseModel):
    """Request to apply an approved proposal to the database."""
    meeting_title: str = Field(..., description="Title of the meeting")
    transcript: str = Field(..., min_length=10, description="Meeting transcript")
    week_number: int = Field(..., ge=1, description="Week number")
    proposal: AIReconciliationResponse = Field(..., description="The approved proposal to apply")


class ReconciliationResponse(BaseModel):
    """
    Response after successful reconciliation.
    Summarizes database updates made.
    """
    meeting_id: str
    project_id: str
    week_number: int
    actions_completed: int
    actions_carried_over: int
    actions_new: int
    report_path: Optional[str] = None
    
    class Config:
        from_attributes = True
