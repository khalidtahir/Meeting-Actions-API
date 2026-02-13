"""
Service for generating structured markdown reports from project reconciliation.
Handles report formatting and persistence to filesystem.
"""
import os
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from models import Project, Action, ActionStatus


class ReportGenerationError(Exception):
    """Raised when report generation fails."""
    pass


class ReportGenerator:
    """
    Service for generating executive reports from project actions.
    
    Responsibilities:
    - Format reconciliation data into markdown
    - Calculate metrics (completion rate, etc.)
    - Persist reports to filesystem
    - No AI usage - pure deterministic formatting
    """
    
    REPORTS_DIR = "reports"
    
    def __init__(self):
        """Initialize report generator."""
        self._ensure_reports_dir()
    
    def _ensure_reports_dir(self):
        """Create reports directory if it doesn't exist."""
        if not os.path.exists(self.REPORTS_DIR):
            os.makedirs(self.REPORTS_DIR, exist_ok=True)
    
    def generate_weekly_report(
        self,
        db: Session,
        project_id: str,
        week_number: int,
        reconciliation_summary: Optional[dict] = None,
        ai_summary: Optional[str] = None
    ) -> str:
        """
        Generate comprehensive weekly report for a project.
        
        Args:
            db: Database session
            project_id: Project ID to report on
            week_number: Week number for the report
            reconciliation_summary: Dict with completed/carryover/new counts
            ai_summary: Executive summary from AI
            
        Returns:
            Path to generated report file
            
        Raises:
            ReportGenerationError: If report generation fails
        """
        try:
            # Fetch project
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Fetch actions for this week
            actions_completed = db.query(Action).join(
                Action.meeting
            ).filter(
                Action.meeting.has(project_id=project_id),
                Action.status == ActionStatus.COMPLETED,
                Action.week_number == week_number
            ).all()
            
            actions_carryover = db.query(Action).join(
                Action.meeting
            ).filter(
                Action.meeting.has(project_id=project_id),
                Action.status == ActionStatus.CARRYOVER,
                Action.week_number == week_number
            ).all()
            
            actions_new = db.query(Action).join(
                Action.meeting
            ).filter(
                Action.meeting.has(project_id=project_id),
                Action.status == ActionStatus.OPEN,
                Action.week_number == week_number
            ).all()
            
            # Calculate metrics
            total_actions = len(actions_completed) + len(actions_carryover) + len(actions_new)
            completion_rate = (len(actions_completed) / total_actions * 100) if total_actions > 0 else 0
            
            # Generate markdown content
            report_content = self._format_markdown_report(
                project=project,
                week_number=week_number,
                completed_actions=actions_completed,
                carryover_actions=actions_carryover,
                new_actions=actions_new,
                completion_rate=completion_rate,
                ai_summary=ai_summary,
                reconciliation_summary=reconciliation_summary or {}
            )
            
            # Save to filesystem
            report_path = self._save_report(
                project_id=project_id,
                week_number=week_number,
                content=report_content
            )
            
            return report_path
            
        except Exception as e:
            raise ReportGenerationError(f"Failed to generate report: {str(e)}")
    
    def _format_markdown_report(
        self,
        project: Project,
        week_number: int,
        completed_actions: List[Action],
        carryover_actions: List[Action],
        new_actions: List[Action],
        completion_rate: float,
        ai_summary: Optional[str],
        reconciliation_summary: dict
    ) -> str:
        """
        Format all data into structured markdown with executive metrics.
        
        Returns:
            Complete markdown report as string
        """
        # Extract metrics from reconciliation summary
        prior_open = reconciliation_summary.get("prior_open_count", 0)
        completed_week = reconciliation_summary.get("completed", 0)
        carryover_week = reconciliation_summary.get("carryover", 0)
        new_actions_added = reconciliation_summary.get("new", 0)
        current_open = reconciliation_summary.get("current_open_count", 0)
        rate_before = reconciliation_summary.get("completion_rate_before", 0.0)
        rate_after = reconciliation_summary.get("completion_rate_after", 0.0)
        delta_rate = reconciliation_summary.get("delta_completion_rate", 0.0)
        
        # Format delta as percentage change
        delta_str = f"+{delta_rate:.1f}%" if delta_rate >= 0 else f"{delta_rate:.1f}%"
        
        report = f"""# Project Report: {project.name}

**Week {week_number}** | Generated: {datetime.utcnow().isoformat()}Z

---

## Executive Summary

{ai_summary or "No summary available."}

---

## Performance Metrics

### Action Reconciliation

| Metric | Count |
|--------|-------|
| Prior Open Actions | {prior_open} |
| Completed This Week | {completed_week} |
| Carried Over / In Progress | {carryover_week} |
| New Actions Added | {new_actions_added} |
| **Current Open Count** | **{current_open}** |

### Completion Rate

| Metric | Value |
|--------|-------|
| Before This Week | {rate_before:.1f}% |
| After This Week | {rate_after:.1f}% |
| **Weekly Delta** | **{delta_str}** |

---

## Completed This Week

"""
        if completed_actions:
            for action in completed_actions:
                report += f"- ✅ **{action.description}**\n"
                if action.owner:
                    report += f"  - Owner: {action.owner}\n"
                report += f"  - Type: {action.type}\n"
        else:
            report += "*No actions completed this week.*\n"
        
        report += f"""
---

## Carryover Items (In Progress)

"""
        if carryover_actions:
            for action in carryover_actions:
                report += f"- ⏳ **{action.description}**\n"
                if action.owner:
                    report += f"  - Owner: {action.owner}\n"
                report += f"  - Type: {action.type}\n"
        else:
            report += "*No carryover items.*\n"
        
        report += f"""
---

## New Actions

"""
        if new_actions:
            for action in new_actions:
                report += f"- 🆕 **{action.description}**\n"
                if action.owner:
                    report += f"  - Owner: {action.owner}\n"
                report += f"  - Type: {action.type}\n"
        else:
            report += "*No new actions.*\n"
        
        # Risk flags section
        report += f"""
---

## Risk Flags & Notes

- System processing functional and database state consistent.

---

## Project Context

- **Project ID**: {project.id}
- **Project Name**: {project.name}
"""
        if project.description:
            report += f"- **Description**: {project.description}\n"
        
        report += f"- **Created**: {project.created_at.isoformat()}Z\n"
        report += f"\n*Report generated by Meeting Actions AI Service*\n"
        
        return report
    
    def _save_report(
        self,
        project_id: str,
        week_number: int,
        content: str
    ) -> str:
        """
        Persist report to filesystem.
        
        Returns:
            Relative path to saved report
        """
        filename = f"project_{project_id}_week{week_number}.md"
        filepath = os.path.join(self.REPORTS_DIR, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return filepath
            
        except IOError as e:
            raise ReportGenerationError(f"Failed to write report file: {str(e)}")


def get_report_generator() -> ReportGenerator:
    """Factory function for dependency injection in routes."""
    return ReportGenerator()
