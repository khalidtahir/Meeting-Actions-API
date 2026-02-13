"""
REST endpoints for meeting operations.
Route handlers should be thin - delegate logic to services.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Meeting, MeetingStatus, Action, Project
from schemas import MeetingCreate, MeetingResponse, MeetingDetailResponse
from services.action_extractor import get_action_extractor, ActionExtractionError

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
def create_meeting(
    meeting_data: MeetingCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new meeting with transcript.
    Meeting must belong to an existing project.
    Initial status is PENDING - call /process to extract actions.
    """
    # Verify project exists
    project = db.query(Project).filter(Project.id == meeting_data.project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {meeting_data.project_id} not found"
        )
    
    # Create meeting entity
    meeting = Meeting(
        project_id=meeting_data.project_id,
        title=meeting_data.title,
        transcript=meeting_data.transcript,
        status=MeetingStatus.PENDING
    )
    
    # Save to database
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    
    return meeting


@router.post("/{meeting_id}/process", response_model=MeetingResponse)
def process_meeting(
    meeting_id: str,
    db: Session = Depends(get_db),
    extractor = Depends(get_action_extractor)
):
    """
    Trigger AI processing to extract action items.
    Updates meeting status and creates action records.
    
    Status flow:
    - PENDING → PROCESSING → DONE (success)
    - PENDING → PROCESSING → FAILED (error)
    """
    # Fetch meeting
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting {meeting_id} not found"
        )
    
    # Only process meetings in PENDING status
    if meeting.status != MeetingStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Meeting already processed (status: {meeting.status})"
        )
    
    # Update status to PROCESSING
    meeting.status = MeetingStatus.PROCESSING
    db.commit()
    
    try:
        # Extract actions using AI
        extracted_actions = extractor.extract_actions(meeting.transcript)
        
        # Convert extracted actions to database models
        for action_data in extracted_actions:
            action = Action(
                meeting_id=meeting.id,
                type=action_data.type,
                description=action_data.description,
                confidence=action_data.confidence
            )
            db.add(action)
        
        # Mark as DONE
        meeting.status = MeetingStatus.DONE
        db.commit()
        db.refresh(meeting)
        
        return meeting
        
    except ActionExtractionError as e:
        # AI extraction failed - mark as FAILED
        meeting.status = MeetingStatus.FAILED
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process meeting: {str(e)}"
        )
    except Exception as e:
        # Unexpected error - rollback and mark FAILED
        db.rollback()
        meeting.status = MeetingStatus.FAILED
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get("/{meeting_id}", response_model=MeetingDetailResponse)
def get_meeting(
    meeting_id: str,
    db: Session = Depends(get_db)
):
    """
    Get meeting details including transcript.
    Use this to check processing status.
    """
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting {meeting_id} not found"
        )
    
    return meeting


@router.get("", response_model=list[MeetingResponse])
def list_meetings(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all meetings (paginated).
    Useful for seeing processing history.
    """
    meetings = db.query(Meeting).offset(skip).limit(limit).all()
    return meetings