"""
SQLAlchemy models representing database tables.
Keep models focused on data structure, not business logic.
"""
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Enum as SQLEnum
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


class Meeting(Base):
    """
    Represents a meeting with its transcript.
    Core entity that owns action items.
    """
    __tablename__ = "meetings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    transcript = Column(Text, nullable=False)
    status = Column(SQLEnum(MeetingStatus), default=MeetingStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship: one meeting has many actions
    actions = relationship("Action", back_populates="meeting", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Meeting(id={self.id}, title={self.title}, status={self.status})>"


class Action(Base):
    """
    Represents an action item extracted from a meeting.
    Always belongs to a meeting (enforced by foreign key).
    """
    __tablename__ = "actions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False)
    type = Column(String, nullable=False)  # e.g., "task", "decision", "follow_up"
    description = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    
    # Relationship: action belongs to one meeting
    meeting = relationship("Meeting", back_populates="actions")
    
    def __repr__(self):
        return f"<Action(id={self.id}, type={self.type}, confidence={self.confidence})>"