"""
Robust Timezone Service
Parses natural language datetime strings in multiple formats
Handles both relative dates (tomorrow, Monday) and absolute dates (7 June, 2025-06-07)

File location: pareto_agents/timezone_service.py
"""

import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TimezoneService:
    """
    Timezone service for parsing natural language datetime strings
    Supports multiple date formats and returns CET datetime objects
    """
    
    # CET timezone offset (UTC+1 in winter, UTC+2 in summer)
    TIMEZONE_CET = "Europe/Zagreb"
    
    def __init__(self):
        """Initialize timezone service"""
        self.current_time = None
    
    def get_current_time_cet(self) -> dict:
        """
        Get current time in CET
        
        Returns:
            dict: Current time information
        """
        try:
            utc_now = datetime.utcnow()
            offset = self._get_utc_offset_hours()
            cet_now = utc_now + timedelta(hours=offset)
            
            return {
                'utc': utc_now.isoformat(),
                'cet': cet_now.isoformat(),
                'formatted': cet_now.strftime('%Y-%m-%d %H:%M:%S CET'),
                'timezone': self.TIMEZONE_CET,
            }
        except Exception as e:
            logger.error(f"Error getting current time: {str(e)}")
            return {}
    
    def parse_datetime_string(self, datetime_str: str) -> datetime:
        """
        Parse datetime string in multiple formats
        
        Supports:
        - Relative: "tomorrow at 2pm", "Monday at 3pm", "in 2 hours"
        - Absolute: "7 June at 4pm", "June 7 at 4pm", "2025-06-07 at 4pm"
        - Verbose: "Tomorrow (2024-06-13) at 16:00 CET"
        - ISO: "2025-12-20T14:30", "2025-12-20 14:30"
        - Time only: "2pm", "14:30"
        
        Args:
            datetime_str (str): Datetime string to parse
            
        Returns:
            datetime: Parsed datetime in CET (naive datetime object)
        """
        if not datetime_str:
            logger.warning("Empty datetime string")
            return None
        
        try:
            logger.debug(f"Parsing datetime string: {datetime_str}")
            
            # Get current time
            utc_now = datetime.utcnow()
            offset = self._get_utc_offset_hours()
            cet_now = utc_now + timedelta(hours=offset)
            
            # Try different parsing strategies in order
            
            # Strategy 1: Verbose format with parentheses - "Tomorrow (2024-06-13) at 16:00 CET"
            result = self._parse_verbose_format(datetime_str, cet_now, offset)
            if result:
                return result
            
            # Strategy 2: Relative dates - "tomorrow at 2pm", "Monday at 3pm", "in 2 hours"
            result = self._parse_relative_format(datetime_str, cet_now, offset)
            if result:
                return result
            
            # Strategy 3: Absolute dates - "7 June at 4pm", "June 7 at 4pm"
            result = self._parse_absolute_format(datetime_str, cet_now, offset)
            if result:
                return result
            
            # Strategy 4: ISO format - "2025-06-07 14:30", "2025-06-07T14:30"
            result = self._parse_iso_format(datetime_str, offset)
            if result:
                return result
            
            # Strategy 5: Time only - "2pm", "14:30"
            result = self._parse_time_only(datetime_str, cet_now, offset)
            if result:
                return result
            
            # If all strategies fail, try dateutil parser as fallback
            result = self._parse_with_dateutil(datetime_str, offset)
            if result:
                return result
            
            logger.warning(f"Could not parse datetime string: {datetime_str}")
            return None
        
        except Exception as e:
            logger.error(f"Error parsing datetime string '{datetime_str}': {str(e)}")
            return None
    
    def _parse_verbose_format(self, datetime_str: str, cet_now: datetime, offset: int) -> datetime:
        """
        Parse verbose format: "Tomorrow (2024-06-13) at 16:00 CET"
        Extract the date from parentheses and time from the string
        """
        try:
            # Extract date from parentheses
            date_match = re.search(r'\((\d{4})-(\d{2})-(\d{2})\)', datetime_str)
            if not date_match:
                return None
            
            year, month, day = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
            
            # Extract time
            time_match = re.search(r'at\s+(\d{1,2}):(\d{2})', datetime_str, re.IGNORECASE)
            if time_match:
                hour, minute = int(time_match.group(1)), int(time_match.group(2))
            else:
                # Default to 9:00 AM if no time specified
                hour, minute = 9, 0
            
            # Create datetime object
            dt = datetime(year, month, day, hour, minute, 0)
            logger.debug(f"Parsed verbose format: {dt}")
            return dt
        
        except Exception as e:
            logger.debug(f"Could not parse verbose format: {str(e)}")
            return None
    
    def _parse_relative_format(self, datetime_str: str, cet_now: datetime, offset: int) -> datetime:
        """
        Parse relative format: "tomorrow at 2pm", "Monday at 3pm", "in 2 hours"
        """
        try:
            datetime_lower = datetime_str.lower()
            
            # Handle "in X hours/minutes"
            in_match = re.search(r'in\s+(\d+)\s+(hours?|minutes?)', datetime_lower)
            if in_match:
                amount = int(in_match.group(1))
                unit = in_match.group(2)
                if 'hour' in unit:
                    return cet_now + timedelta(hours=amount)
                elif 'minute' in unit:
                    return cet_now + timedelta(minutes=amount)
            
            # Handle day names and relative dates
            day_offset = None
            
            if 'tomorrow' in datetime_lower:
                day_offset = 1
            elif 'today' in datetime_lower:
                day_offset = 0
            elif 'monday' in datetime_lower:
                day_offset = self._days_until_weekday('monday', cet_now)
            elif 'tuesday' in datetime_lower:
                day_offset = self._days_until_weekday('tuesday', cet_now)
            elif 'wednesday' in datetime_lower:
                day_offset = self._days_until_weekday('wednesday', cet_now)
            elif 'thursday' in datetime_lower:
                day_offset = self._days_until_weekday('thursday', cet_now)
            elif 'friday' in datetime_lower:
                day_offset = self._days_until_weekday('friday', cet_now)
            elif 'saturday' in datetime_lower:
                day_offset = self._days_until_weekday('saturday', cet_now)
            elif 'sunday' in datetime_lower:
                day_offset = self._days_until_weekday('sunday', cet_now)
            
            if day_offset is not None:
                # Extract time
                time_match = re.search(r'at\s+(\d{1,2}):?(\d{0,2})\s*(am|pm)?', datetime_lower)
                
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2)) if time_match.group(2) else 0
                    am_pm = time_match.group(3)
                    
                    # Convert 12-hour to 24-hour format
                    if am_pm:
                        if am_pm == 'pm' and hour != 12:
                            hour += 12
                        elif am_pm == 'am' and hour == 12:
                            hour = 0
                else:
                    # Default to 9:00 AM
                    hour, minute = 9, 0
                
                # Calculate target date
                target_date = cet_now + timedelta(days=day_offset)
                result = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                logger.debug(f"Parsed relative format: {result}")
                return result
            
            return None
        
        except Exception as e:
            logger.debug(f"Could not parse relative format: {str(e)}")
            return None
    
    def _parse_absolute_format(self, datetime_str: str, cet_now: datetime, offset: int) -> datetime:
        """
        Parse absolute format: "7 June at 4pm", "June 7 at 4pm", "7/6/2025 at 4pm"
        """
        try:
            # Try to extract date and time
            # Pattern 1: "7 June at 4pm" or "7 June 2025 at 4pm"
            pattern1 = r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(?:(\d{4})\s+)?at\s+(\d{1,2}):?(\d{0,2})\s*(am|pm)?'
            match = re.search(pattern1, datetime_str, re.IGNORECASE)
            
            if match:
                day = int(match.group(1))
                month_str = match.group(2)
                year = int(match.group(3)) if match.group(3) else cet_now.year
                hour = int(match.group(4))
                minute = int(match.group(5)) if match.group(5) else 0
                am_pm = match.group(6)
                
                # Convert month string to number
                month = self._month_to_number(month_str)
                
                # Convert 12-hour to 24-hour format
                if am_pm:
                    if am_pm.lower() == 'pm' and hour != 12:
                        hour += 12
                    elif am_pm.lower() == 'am' and hour == 12:
                        hour = 0
                
                result = datetime(year, month, day, hour, minute, 0)
                logger.debug(f"Parsed absolute format (pattern 1): {result}")
                return result
            
            # Pattern 2: "June 7 at 4pm" or "June 7 2025 at 4pm"
            pattern2 = r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})(?:\s+(\d{4}))?\s+at\s+(\d{1,2}):?(\d{0,2})\s*(am|pm)?'
            match = re.search(pattern2, datetime_str, re.IGNORECASE)
            
            if match:
                month_str = match.group(1)
                day = int(match.group(2))
                year = int(match.group(3)) if match.group(3) else cet_now.year
                hour = int(match.group(4))
                minute = int(match.group(5)) if match.group(5) else 0
                am_pm = match.group(6)
                
                # Convert month string to number
                month = self._month_to_number(month_str)
                
                # Convert 12-hour to 24-hour format
                if am_pm:
                    if am_pm.lower() == 'pm' and hour != 12:
                        hour += 12
                    elif am_pm.lower() == 'am' and hour == 12:
                        hour = 0
                
                result = datetime(year, month, day, hour, minute, 0)
                logger.debug(f"Parsed absolute format (pattern 2): {result}")
                return result
            
            return None
        
        except Exception as e:
            logger.debug(f"Could not parse absolute format: {str(e)}")
            return None
    
    def _parse_iso_format(self, datetime_str: str, offset: int) -> datetime:
        """
        Parse ISO format: "2025-06-07 14:30", "2025-06-07T14:30"
        """
        try:
            # Pattern: YYYY-MM-DD[T ]HH:MM
            pattern = r'(\d{4})-(\d{2})-(\d{2})[T ](\d{1,2}):(\d{2})'
            match = re.search(pattern, datetime_str)
            
            if match:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
                hour = int(match.group(4))
                minute = int(match.group(5))
                
                result = datetime(year, month, day, hour, minute, 0)
                logger.debug(f"Parsed ISO format: {result}")
                return result
            
            return None
        
        except Exception as e:
            logger.debug(f"Could not parse ISO format: {str(e)}")
            return None
    
    def _parse_time_only(self, datetime_str: str, cet_now: datetime, offset: int) -> datetime:
        """
        Parse time only: "2pm", "14:30", "2:30pm"
        Uses today's date
        """
        try:
            datetime_lower = datetime_str.lower().strip()
            
            # Pattern: HH:MM or H:MM or H or HH followed by am/pm
            pattern = r'^(\d{1,2}):?(\d{0,2})\s*(am|pm)?$'
            match = re.search(pattern, datetime_lower)
            
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2)) if match.group(2) else 0
                am_pm = match.group(3)
                
                # Convert 12-hour to 24-hour format
                if am_pm:
                    if am_pm == 'pm' and hour != 12:
                        hour += 12
                    elif am_pm == 'am' and hour == 12:
                        hour = 0
                
                result = cet_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                logger.debug(f"Parsed time only: {result}")
                return result
            
            return None
        
        except Exception as e:
            logger.debug(f"Could not parse time only: {str(e)}")
            return None
    
    def _parse_with_dateutil(self, datetime_str: str, offset: int) -> datetime:
        """
        Fallback: Try simple parsing strategies without external libraries
        """
        try:
            # Try to extract any numbers and parse them
            # This is a very basic fallback
            numbers = re.findall(r'\d+', datetime_str)
            if not numbers:
                return None
            
            # If we have at least 2 numbers, try to parse as hour:minute
            if len(numbers) >= 2:
                try:
                    hour = int(numbers[-2])
                    minute = int(numbers[-1])
                    
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        utc_now = datetime.utcnow()
                        offset_hours = self._get_utc_offset_hours()
                        cet_now = utc_now + timedelta(hours=offset_hours)
                        result = cet_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        logger.debug(f"Parsed with fallback strategy: {result}")
                        return result
                except (ValueError, IndexError):
                    pass
            
            logger.debug(f"Could not parse with fallback strategy")
            return None
        
        except Exception as e:
            logger.debug(f"Error in fallback parser: {str(e)}")
            return None
    
    def _get_utc_offset_hours(self) -> int:
        """
        Get UTC offset for CET (Europe/Zagreb)
        Returns 1 for winter (CET, UTC+1) or 2 for summer (CEST, UTC+2)
        """
        try:
            utc_now = datetime.utcnow()
            
            # DST in Europe: last Sunday of March to last Sunday of October
            # For simplicity, check if we're in DST period
            march_last_sunday = self._get_last_sunday(utc_now.year, 3)
            october_last_sunday = self._get_last_sunday(utc_now.year, 10)
            
            if march_last_sunday <= utc_now.date() < october_last_sunday:
                return 2  # CEST (UTC+2)
            else:
                return 1  # CET (UTC+1)
        
        except Exception as e:
            logger.warning(f"Error calculating UTC offset: {str(e)}, defaulting to UTC+1")
            return 1
    
    def _get_last_sunday(self, year: int, month: int) -> datetime:
        """Get the last Sunday of a given month"""
        # Start from the last day of the month
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        
        last_day = next_month - timedelta(days=1)
        
        # Go back to the last Sunday
        while last_day.weekday() != 6:  # 6 = Sunday
            last_day -= timedelta(days=1)
        
        return last_day.date()
    
    def _days_until_weekday(self, weekday_name: str, current_date: datetime) -> int:
        """
        Calculate days until the next occurrence of a weekday
        
        Args:
            weekday_name (str): Name of weekday (e.g., 'monday')
            current_date (datetime): Current date
            
        Returns:
            int: Number of days until that weekday
        """
        weekdays = {
            'monday': 0,
            'tuesday': 1,
            'wednesday': 2,
            'thursday': 3,
            'friday': 4,
            'saturday': 5,
            'sunday': 6,
        }
        
        target_weekday = weekdays.get(weekday_name.lower())
        if target_weekday is None:
            return None
        
        current_weekday = current_date.weekday()
        days_ahead = target_weekday - current_weekday
        
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        return days_ahead
    
    def _month_to_number(self, month_str: str) -> int:
        """Convert month name to number"""
        months = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12,
        }
        return months.get(month_str.lower(), 1)
