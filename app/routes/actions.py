"""
REST endpoints for action item operations.
Focused on retrieving extracted actions.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Meeting, Action
from schemas import MeetingActionsResponse, ActionResponse

router = APIRouter(prefix="/meetings", tags=["actions"])


@router.get("/{meeting_id}/actions", response_model=MeetingActionsResponse)
def get_meeting_actions(
    meeting_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all action items extracted from a meeting.
    Returns empty list if meeting hasn't been processed yet.
    """
    # Fetch meeting with actions (using eager loading for efficiency)
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting {meeting_id} not found"
        )
    
    # Build response with meeting context and actions
    return MeetingActionsResponse(
        meeting_id=meeting.id,
        meeting_title=meeting.title,
        status=meeting.status,
        actions=[ActionResponse.model_validate(action) for action in meeting.actions]
    )


@router.get("/{meeting_id}/actions/{action_id}", response_model=ActionResponse)
def get_action(
    meeting_id: str,
    action_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific action item by ID.
    Validates that action belongs to specified meeting.
    """
    action = db.query(Action).filter(
        Action.id == action_id,
        Action.meeting_id == meeting_id
    ).first()
    
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action {action_id} not found in meeting {meeting_id}"
        )
    
    return action