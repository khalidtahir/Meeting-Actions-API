"""
REST endpoints for project operations.
Handles project creation, retrieval, and action reconciliation.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Project, Meeting, MeetingStatus
from schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectDetailResponse,
    MeetingResponse,
    ReconciliationRequest,
    ReconciliationResponse
)
from services.project_reconciler import (
    ProjectReconciler,
    ProjectReconciliationError,
    get_project_reconciler
)
from services.report_generator import (
    ReportGenerator,
    get_report_generator
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new project.
    
    A project groups related meetings and enables cross-meeting
    action reconciliation and tracking.
    """
    project = Project(
        name=project_data.name,
        description=project_data.description
    )
    
    db.add(project)
    db.commit()
    db.refresh(project)
    
    return project


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Get project details including meeting count.
    
    Provides overview of project activity and configuration.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    # Count meetings in project
    meeting_count = len(project.meetings)
    
    return ProjectDetailResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        meeting_count=meeting_count
    )


@router.post("/{project_id}/reconcile", response_model=ReconciliationResponse)
def reconcile_project(
    project_id: str,
    reconciliation_data: ReconciliationRequest,
    db: Session = Depends(get_db),
    reconciler = Depends(get_project_reconciler),
    report_gen = Depends(get_report_generator)
):
    """
    Trigger AI-powered reconciliation for a project.
    
    Flow:
    1. Create new meeting entry
    2. Fetch all OPEN actions for project
    3. Call LLM for reconciliation (with prior actions + transcript)
    4. Deterministically update action statuses
    5. Create new actions from reconciliation result
    6. Generate weekly report
    7. Return reconciliation summary
    
    Reconciliation bridges multiple meetings by:
    - Determining which prior actions are now COMPLETED
    - Carrying forward still-pending actions
    - Extracting new actions from new meeting
    - Generating executive summary
    """
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    try:
        # Execute reconciliation
        meeting, reconciliation_result, update_summary = reconciler.reconcile_project(
            db=db,
            project_id=project_id,
            meeting_title=reconciliation_data.meeting_title,
            transcript=reconciliation_data.transcript,
            week_number=reconciliation_data.week_number
        )
        
        # Generate weekly report
        report_path = report_gen.generate_weekly_report(
            db=db,
            project_id=project_id,
            week_number=reconciliation_data.week_number,
            reconciliation_summary=update_summary,
            ai_summary=reconciliation_result.summary
        )
        
        return ReconciliationResponse(
            meeting_id=meeting.id,
            project_id=project.id,
            week_number=reconciliation_data.week_number,
            actions_completed=update_summary.get("completed", 0),
            actions_carried_over=update_summary.get("carryover", 0),
            actions_new=update_summary.get("new", 0),
            report_path=report_path
        )
        
    except ProjectReconciliationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reconciliation failed: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during reconciliation: {str(e)}"
        )


@router.get("/{project_id}/meetings")
def get_project_meetings(
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all meetings in a project (paginated).
    
    Useful for viewing all meetings associated with a project
    and their processing status.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    # Fetch meetings for this project
    meetings = db.query(Meeting).filter(
        Meeting.project_id == project_id
    ).offset(skip).limit(limit).all()
    
    # Return basic meeting info with response model
    return [MeetingResponse.model_validate(m) for m in meetings]
