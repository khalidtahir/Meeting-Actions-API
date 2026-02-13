"""
SQLAlchemy models representing database tables.
Keep models focused on data structure, not business logic.
"""
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from database import Base


class MeetingStatus(str, enum.Enum):
    """
    Meeting processing status.
    String enum for easy JSON serialization.
    """
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


class ActionStatus(str, enum.Enum):
    """
    Action item status in the project lifecycle.
    Tracks completion and carryover across meetings.
    """
    OPEN = "OPEN"
    COMPLETED = "COMPLETED"
    CARRYOVER = "CARRYOVER"


class Project(Base):
    """
    Represents a project that groups related meetings.
    Central entity for tracking actions and reconciliation across multiple meetings.
    """
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship: one project has many meetings
    meetings = relationship("Meeting", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name})>"


class Meeting(Base):
    """
    Represents a meeting with its transcript.
    Belongs to a project and owns multiple action items.
    """
    __tablename__ = "meetings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    title = Column(String, nullable=False)
    transcript = Column(Text, nullable=False)
    status = Column(SQLEnum(MeetingStatus), default=MeetingStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship: meeting belongs to one project
    project = relationship("Project", back_populates="meetings")
    
    # Relationship: one meeting has many actions
    actions = relationship("Action", back_populates="meeting", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Meeting(id={self.id}, project_id={self.project_id}, title={self.title}, status={self.status})>"


class Action(Base):
    """
    Represents an action item extracted from a meeting.
    Always belongs to a meeting (enforced by foreign key).
    Tracks completion status and carryover across weeks.
    """
    __tablename__ = "actions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False)
    type = Column(String, nullable=False)  # e.g., "task", "decision", "follow_up"
    description = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    status = Column(SQLEnum(ActionStatus), default=ActionStatus.OPEN, nullable=False)  # OPEN, COMPLETED, CARRYOVER
    week_number = Column(Integer, nullable=True)  # Week number for tracking across meetings
    owner = Column(String, nullable=True)  # Optional: person responsible
    
    # Relationship: action belongs to one meeting
    meeting = relationship("Meeting", back_populates="actions")
    
    def __repr__(self):
        return f"<Action(id={self.id}, type={self.type}, status={self.status}, confidence={self.confidence})>"