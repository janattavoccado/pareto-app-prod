"""
Task Executors - Complex Multi-Step Operations
Handles complex tasks like summaries, lists, and combined operations

File location: pareto_agents/task_executors.py
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Task Models (Pydantic)
# ============================================================================

class DailySummaryRequest(BaseModel):
    """Request model for daily summary task"""
    phone_number: str = Field(..., description="User's phone number")
    include_emails: bool = Field(True, description="Include email summary")
    include_calendar: bool = Field(True, description="Include calendar summary")
    email_limit: int = Field(5, description="Max unread emails to show")
    format_type: str = Field("text", description="Output format: text, html, markdown")


class MeetingPrepRequest(BaseModel):
    """Request model for meeting preparation task"""
    phone_number: str = Field(..., description="User's phone number")
    date: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")
    hours_before: int = Field(2, description="Hours before meetings to prepare")


class WeeklySummaryRequest(BaseModel):
    """Request model for weekly summary task"""
    phone_number: str = Field(..., description="User's phone number")
    include_metrics: bool = Field(True, description="Include meeting/email metrics")


# ============================================================================
# Task Result Models
# ============================================================================

class TaskResult(BaseModel):
    """Result model for task execution"""
    success: bool
    task_type: str
    summary: str
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# Daily Summary Executor
# ============================================================================

def execute_daily_summary(request: DailySummaryRequest) -> TaskResult:
    """
    Execute a daily summary task combining calendar and email information
    
    Args:
        request: DailySummaryRequest with task parameters
        
    Returns:
        TaskResult with combined summary
    """
    try:
        logger.info(f"Executing daily summary for {request.phone_number}")
        
        from .assistant_tools import (
            get_calendar_events,
            get_email_summary,
            format_calendar_list,
            format_email_list,
        )
        
        summary_parts = []
        data = {}
        
        # Get calendar events
        if request.include_calendar:
            logger.debug("Fetching calendar events for daily summary")
            calendar_result = get_calendar_events(
                phone_number=request.phone_number,
                operation="list_today",
                include_details=False
            )
            data["calendar"] = calendar_result
            
            if calendar_result.get("success"):
                summary_parts.append(f"📅 **Calendar**: {calendar_result.get('summary')}")
                if calendar_result.get("events"):
                    summary_parts.append(format_calendar_list(calendar_result.get("events")))
        
        # Get email summary
        if request.include_emails:
            logger.debug("Fetching email summary for daily summary")
            email_result = get_email_summary(
                phone_number=request.phone_number,
                operation="list_unread",
                limit=request.email_limit
            )
            data["emails"] = email_result
            
            if email_result.get("success"):
                summary_parts.append(f"📧 **Emails**: {email_result.get('summary')}")
                if email_result.get("emails"):
                    summary_parts.append(format_email_list(email_result.get("emails")))
        
        # Combine summary
        if request.format_type == "markdown":
            combined_summary = "\n\n".join(summary_parts)
        elif request.format_type == "html":
            combined_summary = "<br><br>".join(summary_parts)
        else:  # text
            combined_summary = "\n\n".join(summary_parts)
        
        logger.info(f"Daily summary generated successfully")
        
        return TaskResult(
            success=True,
            task_type="daily_summary",
            summary=combined_summary,
            data=data
        )
    
    except Exception as e:
        logger.error(f"Error executing daily summary: {str(e)}", exc_info=True)
        return TaskResult(
            success=False,
            task_type="daily_summary",
            summary="",
            error=str(e)
        )


# ============================================================================
# Meeting Preparation Executor
# ============================================================================

def execute_meeting_prep(request: MeetingPrepRequest) -> TaskResult:
    """
    Execute meeting preparation task - get upcoming meetings and relevant info
    
    Args:
        request: MeetingPrepRequest with task parameters
        
    Returns:
        TaskResult with meeting preparation info
    """
    try:
        logger.info(f"Executing meeting prep for {request.phone_number}")
        
        from .assistant_tools import (
            get_calendar_events,
            format_calendar_list,
        )
        
        # Get today's or specified date's events
        target_date = request.date if request.date else datetime.now().strftime("%Y-%m-%d")
        
        calendar_result = get_calendar_events(
            phone_number=request.phone_number,
            operation="list_date",
            date=target_date,
            include_details=True
        )
        
        if not calendar_result.get("success"):
            return TaskResult(
                success=False,
                task_type="meeting_prep",
                summary="",
                error="Could not fetch calendar events"
            )
        
        events = calendar_result.get("events", [])
        
        # Filter events within the specified hours
        upcoming_events = []
        now = datetime.now()
        cutoff_time = now + timedelta(hours=request.hours_before)
        
        for event in events:
            try:
                event_start = datetime.fromisoformat(event.get("start", "").replace("Z", "+00:00"))
                if now <= event_start <= cutoff_time:
                    upcoming_events.append(event)
            except (ValueError, AttributeError):
                # If we can't parse the time, include it anyway
                upcoming_events.append(event)
        
        # Generate preparation summary
        summary_lines = [
            f"🎯 **Meeting Preparation for {target_date}**",
            f"Upcoming meetings in the next {request.hours_before} hours:",
            ""
        ]
        
        if upcoming_events:
            summary_lines.append(format_calendar_list(upcoming_events))
            summary_lines.append("")
            summary_lines.append("**Preparation Tips:**")
            summary_lines.append("- Review meeting agendas and attendees")
            summary_lines.append("- Prepare relevant documents and materials")
            summary_lines.append("- Check for any pre-meeting requirements")
        else:
            summary_lines.append("No meetings scheduled in the specified timeframe.")
        
        combined_summary = "\n".join(summary_lines)
        
        logger.info(f"Meeting prep generated successfully")
        
        return TaskResult(
            success=True,
            task_type="meeting_prep",
            summary=combined_summary,
            data={
                "target_date": target_date,
                "upcoming_events": upcoming_events,
                "event_count": len(upcoming_events)
            }
        )
    
    except Exception as e:
        logger.error(f"Error executing meeting prep: {str(e)}", exc_info=True)
        return TaskResult(
            success=False,
            task_type="meeting_prep",
            summary="",
            error=str(e)
        )


# ============================================================================
# Weekly Summary Executor
# ============================================================================

def execute_weekly_summary(request: WeeklySummaryRequest) -> TaskResult:
    """
    Execute weekly summary task - overview of the week
    
    Args:
        request: WeeklySummaryRequest with task parameters
        
    Returns:
        TaskResult with weekly summary
    """
    try:
        logger.info(f"Executing weekly summary for {request.phone_number}")
        
        from .assistant_tools import (
            get_calendar_events,
            get_email_summary,
            format_calendar_list,
        )
        
        # Get week's events
        calendar_result = get_calendar_events(
            phone_number=request.phone_number,
            operation="list_week",
            include_details=False
        )
        
        # Get email summary
        email_result = get_email_summary(
            phone_number=request.phone_number,
            operation="get_summary",
            limit=20
        )
        
        summary_lines = ["📊 **Weekly Summary**", ""]
        
        # Calendar section
        if calendar_result.get("success"):
            events = calendar_result.get("events", [])
            summary_lines.append(f"**Calendar**: {len(events)} events this week")
            if events and request.include_metrics:
                summary_lines.append(format_calendar_list(events[:5]))  # Show top 5
                if len(events) > 5:
                    summary_lines.append(f"... and {len(events) - 5} more events")
            summary_lines.append("")
        
        # Email section
        if email_result.get("success"):
            emails = email_result.get("emails", [])
            summary_lines.append(f"**Emails**: {len(emails)} recent messages")
            if request.include_metrics:
                summary_lines.append(f"- Unread: {email_result.get('count', 0)} messages")
            summary_lines.append("")
        
        # Add weekly insights
        if request.include_metrics:
            summary_lines.append("**Weekly Insights:**")
            summary_lines.append(f"- Total meetings: {calendar_result.get('count', 0)}")
            summary_lines.append(f"- Email activity: {email_result.get('count', 0)} messages")
        
        combined_summary = "\n".join(summary_lines)
        
        logger.info(f"Weekly summary generated successfully")
        
        return TaskResult(
            success=True,
            task_type="weekly_summary",
            summary=combined_summary,
            data={
                "calendar_events": calendar_result.get("count", 0),
                "email_count": email_result.get("count", 0),
            }
        )
    
    except Exception as e:
        logger.error(f"Error executing weekly summary: {str(e)}", exc_info=True)
        return TaskResult(
            success=False,
            task_type="weekly_summary",
            summary="",
            error=str(e)
        )


# ============================================================================
# Task Dispatcher
# ============================================================================

def execute_task(task_type: str, request_data: Dict[str, Any]) -> TaskResult:
    """
    Dispatch and execute a task based on type
    
    Args:
        task_type: Type of task to execute
        request_data: Task request data
        
    Returns:
        TaskResult with execution result
    """
    try:
        logger.info(f"Executing task: {task_type}")
        
        if task_type == "daily_summary":
            request = DailySummaryRequest(**request_data)
            return execute_daily_summary(request)
        
        elif task_type == "meeting_prep":
            request = MeetingPrepRequest(**request_data)
            return execute_meeting_prep(request)
        
        elif task_type == "weekly_summary":
            request = WeeklySummaryRequest(**request_data)
            return execute_weekly_summary(request)
        
        else:
            logger.error(f"Unknown task type: {task_type}")
            return TaskResult(
                success=False,
                task_type=task_type,
                summary="",
                error=f"Unknown task type: {task_type}"
            )
    
    except Exception as e:
        logger.error(f"Error executing task: {str(e)}", exc_info=True)
        return TaskResult(
            success=False,
            task_type=task_type,
            summary="",
            error=str(e)
        )
