"""
Service for reconciling actions across multiple meetings within a project.
Handles LLM-based reconciliation, state tracking, and deterministic database updates.
"""
import json
import logging
from typing import List, Tuple
from pydantic import ValidationError
from openai import OpenAI
from anthropic import Anthropic
from sqlalchemy.orm import Session

from config import get_settings
from models import Action, ActionStatus, Meeting, MeetingStatus
from schemas import AIReconciliationResponse, PriorActionReference, ReconciliationActionItem

# Configure logging
logger = logging.getLogger(__name__)


class ProjectReconciliationError(Exception):
    """Raised when project reconciliation fails."""
    pass


class ProjectReconciler:
    """
    Service for reconciling project actions across meetings.
    
    Responsibilities:
    - Fetch prior OPEN actions
    - Call LLM once with structured input
    - Parse strict JSON response
    - Deterministically update database state
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.client = None
    
    def reconcile_project(
        self,
        db: Session,
        project_id: str,
        meeting_title: str,
        transcript: str,
        week_number: int
    ) -> Tuple[Meeting, AIReconciliationResponse, dict]:
        """
        Execute full reconciliation flow for a project.
        
        Args:
            db: Database session
            project_id: Project ID to reconcile
            meeting_title: Title of new meeting being processed
            transcript: Transcript of new meeting
            week_number: Week number for tracking
            
        Returns:
            Tuple of (meeting_db_object, reconciliation_result, update_summary)
            
        Raises:
            ProjectReconciliationError: If reconciliation fails
        """
        try:
            # Create meeting record
            meeting = Meeting(
                project_id=project_id,
                title=meeting_title,
                transcript=transcript,
                status=MeetingStatus.PENDING
            )
            db.add(meeting)
            db.flush()  # Flush to get meeting ID, don't commit yet
            
            # Fetch all OPEN actions for this project
            open_actions = db.query(Action).join(Meeting).filter(
                Meeting.project_id == project_id,
                Action.status == ActionStatus.OPEN
            ).all()
            
            # Call LLM for reconciliation
            reconciliation = self._call_llm_reconcile(
                open_actions=open_actions,
                transcript=transcript
            )
            
            # Deterministically update database based on LLM response
            summary = self._apply_reconciliation(
                db=db,
                meeting=meeting,
                open_actions=open_actions,
                reconciliation=reconciliation,
                week_number=week_number
            )
            
            # Mark meeting as processed
            meeting.status = MeetingStatus.DONE
            db.commit()
            db.refresh(meeting)
            
            return meeting, reconciliation, summary
            
        except Exception as e:
            db.rollback()
            raise ProjectReconciliationError(f"Reconciliation failed: {str(e)}")
    
    def _call_llm_reconcile(
        self,
        open_actions: List[Action],
        transcript: str
    ) -> AIReconciliationResponse:
        """
        Call LLM once with structured prompt for reconciliation.
        
        Args:
            open_actions: List of currently OPEN actions
            transcript: New meeting transcript
            
        Returns:
            Parsed AIReconciliationResponse with structured JSON
            
        Raises:
            ProjectReconciliationError: If LLM call fails or returns invalid JSON
        """
        # Handle mock mode
        if not self.settings.ai_api_key:
            return self._generate_mock_reconciliation(open_actions, transcript)
        
        # Initialize client if needed
        if self.client is None:
            if self.settings.ai_provider == "openai":
                self.client = OpenAI(api_key=self.settings.ai_api_key)
            elif self.settings.ai_provider == "anthropic":
                self.client = Anthropic(api_key=self.settings.ai_api_key)
            else:
                raise ValueError(f"Unsupported AI provider: {self.settings.ai_provider}")
        
        try:
            # Build prompt
            prompt = self._build_reconciliation_prompt(open_actions, transcript)
            
            # Call appropriate provider
            if self.settings.ai_provider == "openai":
                raw_response = self._call_openai(prompt)
            else:
                raw_response = self._call_anthropic(prompt)
            
            # Parse response
            return self._parse_reconciliation_response(raw_response)
            
        except Exception as e:
            raise ProjectReconciliationError(f"LLM reconciliation failed: {str(e)}")
    
    def _build_reconciliation_prompt(
        self,
        open_actions: List[Action],
        transcript: str
    ) -> str:
        """
        Build structured prompt for LLM reconciliation.
        
        Input: Prior open actions (with IDs) + new transcript
        Output: Structured JSON referencing action IDs for completed/carryover
        
        Critical: Action IDs must be used for matching, not descriptions.
        """
        # Format open actions as JSON with required ID field
        open_actions_json = json.dumps([
            {
                "id": action.id,
                "description": action.description,
                "owner": action.owner or "unassigned",
                "type": action.type
            }
            for action in open_actions
        ], indent=2)
        
        return f"""You are an AI assistant that reconciles action items across meetings.

Given:
1. A list of currently OPEN actions from prior meetings (with system IDs)
2. A new meeting transcript

Your task:
- Determine which prior OPEN actions are now COMPLETED based on the transcript
- Determine which prior OPEN actions should CARRYOVER (not yet done)
- Extract NEW actions from the transcript
- Identify RISK FLAGS (concerns, blockers, dependencies)
- Provide an executive SUMMARY paragraph

CRITICAL: When marking prior OPEN actions as completed or carryover, you MUST:
- Include the EXACT original ID from the list below (do not invent or modify IDs)
- Include the current description and owner
- Only reference actions by their original ID

Prior OPEN Actions:
{open_actions_json}

New Meeting Transcript:
{transcript}

Return ONLY valid JSON in this EXACT format, with no additional text or commentary:
{{
  "completed": [
    {{"id": "action-uuid", "description": "what was completed", "owner": "person name"}},
  ],
  "carryover": [
    {{"id": "action-uuid", "description": "still pending", "owner": "person name"}},
  ],
  "new_actions": [
    {{"description": "new action extracted from transcript", "owner": "person name"}},
  ],
  "risk_flags": [
    "concern or blocker",
  ],
  "summary": "One paragraph executive summary of meeting outcomes and status."
}}

IMPORTANT:
- "completed" and "carryover" MUST include the original ID field
- "new_actions" MUST NOT include IDs (these are new)
- Use empty arrays [] for any empty categories
- Return ONLY the JSON object with no markdown, code blocks, or commentary

JSON Response:"""
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API and return response."""
        response = self.client.chat.completions.create(
            model=self.settings.ai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that reconciles action items. Always respond with valid JSON only. Do not include any explanatory text before or after the JSON."
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
        """Call Anthropic API and return response."""
        response = self.client.messages.create(
            model=self.settings.ai_model,
            max_tokens=self.settings.ai_max_tokens,
            system="You are a helpful assistant that reconciles action items. Always respond with valid JSON only. Do not include any explanatory text before or after the JSON.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        return response.content[0].text
    
    def _parse_reconciliation_response(self, raw_response: str) -> AIReconciliationResponse:
        """
        Parse and validate JSON response from LLM.
        
        Raises:
            ProjectReconciliationError: If JSON is invalid or schema doesn't match
        """
        try:
            # Extract JSON from response (in case there's any surrounding text)
            # Look for { and } delimiters
            start_idx = raw_response.find('{')
            end_idx = raw_response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            
            json_str = raw_response[start_idx:end_idx]
            json_data = json.loads(json_str)
            
            # Validate against schema
            reconciliation = AIReconciliationResponse(**json_data)
            return reconciliation
            
        except json.JSONDecodeError as e:
            raise ProjectReconciliationError(f"Invalid JSON in LLM response: {str(e)}")
        except ValidationError as e:
            raise ProjectReconciliationError(f"Response schema validation failed: {str(e)}")
    
    def _apply_reconciliation(
        self,
        db: Session,
        meeting: Meeting,
        open_actions: List[Action],
        reconciliation: AIReconciliationResponse,
        week_number: int
    ) -> dict:
        """
        Deterministically apply reconciliation results to database.
        
        Matching is ID-based only - uses EXACT action IDs from reconciliation.
        
        Updates made:
        1. Mark actions in "completed" as COMPLETED
        2. Mark actions in "carryover" as CARRYOVER
        3. Warn/default any unmatched actions to CARRYOVER (fail-safe)
        4. Create new actions from reconciliation output
        5. Calculate comprehensive metrics for reporting
        
        Returns:
            Summary dict with action counts and metrics
        """
        summary = {
            "completed": 0,
            "carryover": 0,
            "new": 0,
            "prior_open_count": len(open_actions),
            "current_open_count": 0,
            "completion_rate_before": 0.0,
            "completion_rate_after": 0.0,
            "delta_completion_rate": 0.0
        }
        
        # Create comprehensive lookup by action ID
        action_by_id = {action.id: action for action in open_actions}
        
        # Parse completed action IDs from reconciliation
        completed_ids = {item.id for item in reconciliation.completed}
        carryover_ids = {item.id for item in reconciliation.carryover}
        
        # Comprehensive set of explicitly mentioned IDs
        mentioned_ids = completed_ids | carryover_ids
        
        # Track which actions were handled
        processed_actions = set()
        
        # ============= Mark completed actions =============
        for completed_item in reconciliation.completed:
            action = action_by_id.get(completed_item.id)
            if action is None:
                logger.warning(
                    f"Reconciliation referenced unknown action ID: {completed_item.id}. Skipping."
                )
                continue
            
            action.status = ActionStatus.COMPLETED
            action.week_number = week_number
            # Update owner if provided by LLM
            if completed_item.owner and completed_item.owner != "unassigned":
                action.owner = completed_item.owner
            
            processed_actions.add(action.id)
            summary["completed"] += 1
        
        # ============= Mark carryover actions =============
        for carryover_item in reconciliation.carryover:
            action = action_by_id.get(carryover_item.id)
            if action is None:
                logger.warning(
                    f"Reconciliation referenced unknown action ID: {carryover_item.id}. Skipping."
                )
                continue
            
            action.status = ActionStatus.CARRYOVER
            action.week_number = week_number
            # Update owner if provided by LLM
            if carryover_item.owner and carryover_item.owner != "unassigned":
                action.owner = carryover_item.owner
            
            processed_actions.add(action.id)
            summary["carryover"] += 1
        
        # ============= Handle unmatched actions (fail-safe) =============
        unmatched = set(action_by_id.keys()) - mentioned_ids
        if unmatched:
            logger.warning(
                f"Reconciliation did not mention {len(unmatched)} open actions. "
                f"Defaulting them to CARRYOVER as fail-safe. IDs: {unmatched}"
            )
            for action_id in unmatched:
                action = action_by_id[action_id]
                action.status = ActionStatus.CARRYOVER
                action.week_number = week_number
                processed_actions.add(action.id)
                summary["carryover"] += 1
        
        # ============= Create new actions from reconciliation =============
        for item in reconciliation.new_actions:
            new_action = Action(
                meeting_id=meeting.id,
                type="task",  # Default type for reconciliation-generated actions
                description=item.description,
                confidence=0.95,  # High confidence for AI-extracted actions
                status=ActionStatus.OPEN,
                week_number=week_number,
                owner=item.owner if item.owner and item.owner != "unassigned" else None
            )
            db.add(new_action)
            summary["new"] += 1
        
        # ============= Calculate completion metrics =============
        # Current open count includes carryover + new actions added
        summary["current_open_count"] = summary["carryover"] + summary["new"]
        
        # Completion rate for this period
        # before: 0 (no actions completed yet at start)
        # after: completed / (completed + current_open)
        total_actions_this_period = summary["completed"] + summary["current_open_count"]
        
        summary["completion_rate_before"] = 0.0
        
        if total_actions_this_period > 0:
            summary["completion_rate_after"] = (
                summary["completed"] / total_actions_this_period * 100.0
            )
        else:
            summary["completion_rate_after"] = 0.0
        
        summary["delta_completion_rate"] = (
            summary["completion_rate_after"] - summary["completion_rate_before"]
        )
        
        logger.info(
            f"Reconciliation metrics - "
            f"Completed: {summary['completed']}, "
            f"Carryover: {summary['carryover']}, "
            f"New: {summary['new']}, "
            f"Completion Rate: {summary['completion_rate_after']:.1f}%"
        )
        
        return summary
    
    def _generate_mock_reconciliation(
        self,
        open_actions: List[Action],
        transcript: str
    ) -> AIReconciliationResponse:
        """
        Generate deterministic mock reconciliation for testing without API key.
        Uses ID-based matching to match new schema format.
        """
        completed = []
        carryover = []
        
        # Simple heuristic: if action description appears in transcript, mark completed
        for action in open_actions:
            if action.description.lower() in transcript.lower():
                # Completed: include original ID
                item = PriorActionReference(
                    id=action.id,
                    description=action.description,
                    owner=action.owner
                )
                completed.append(item)
            else:
                # Carryover: include original ID
                item = PriorActionReference(
                    id=action.id,
                    description=action.description,
                    owner=action.owner
                )
                carryover.append(item)
        
        # Mock new actions from transcript (no IDs)
        new_actions = [
            ReconciliationActionItem(
                description="Review meeting notes and send summary to team",
                owner="Meeting Organizer"
            )
        ]
        
        return AIReconciliationResponse(
            completed=completed,
            carryover=carryover,
            new_actions=new_actions,
            risk_flags=["Ensure follow-up actions are assigned to specific owners"],
            summary="Meeting covered planned topics. Some actions have been completed, while others require continued attention in next period."
        )


def get_project_reconciler() -> ProjectReconciler:
    """Factory function for dependency injection in routes."""
    return ProjectReconciler()
