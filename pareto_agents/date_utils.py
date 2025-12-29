import datetime
import pytz

# The user specified GMT+1 / CET timezone
TIMEZONE = pytz.timezone('Europe/Paris') # CET/CEST is equivalent to Europe/Paris

def get_current_date_context() -> str:
    """
    Returns the current date and time context string for the Personal Assistant agent.
    
    Returns:
        str: A formatted string containing the current date, time, and timezone.
    """
    now = datetime.datetime.now(TIMEZONE)
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    timezone_name = now.tzname()
    
    # The user is in GMT+1. The current date is 2025-12-29.
    # The agent needs to know the current date and timezone.
    
    context_string = (
        f"Today's date is {current_date}. The current time is {current_time}. "
        f"The user is in the {timezone_name} timezone (GMT+1/CET). "
        "You MUST use this date and timezone for all calculations. "
        "When the user mentions relative dates like 'tomorrow', 'next Monday', 'in 3 days', "
        "interpret them relative to this current date and time."
    )
    return context_string

def get_current_date_str() -> str:
    """
    Returns the current date string (YYYY-MM-DD) in the specified timezone.
    """
    now = datetime.datetime.now(TIMEZONE)
    return now.strftime("%Y-%m-%d")
