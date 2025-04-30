import re
import time
import logging
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Иерархия ролей для проверки прав доступа
ROLE_HIERARCHY = {
    "user": 0,
    "moderator": 1,
    "senior_moderator": 2,
    "admin": 3,
    "creator": 4
}

def parse_command(text: str) -> Tuple[str, str]:
    # Parse command from text.
#
# Args:
# text: Command text
#
# Returns:
# Tuple of command name and arguments
    # Remove leading slash
    if text.startswith('/'):
        text = text[1:]
    
    # Split command and arguments
    parts = text.split(' ', 1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    
    return command, args

def parse_time(time_str: str) -> int:
    # Parse time string to seconds.
#
# Args:
# time_str: Time string (e.g. 1h, 30m, 1d)
#
# Returns:
# Time in seconds
    if not time_str:
        raise ValueError("Empty time string")
    
    # Match numbers followed by a time unit (s, m, h, d)
    match = re.match(r'^(\d+)([smhd])$', time_str.lower())
    if not match:
        raise ValueError(f"Invalid time format: {time_str}")
    
    value, unit = match.groups()
    value = int(value)
    
    if unit == 's':
        return value
    elif unit == 'm':
        return value * 60
    elif unit == 'h':
        return value * 3600
    elif unit == 'd':
        return value * 86400
    else:
        raise ValueError(f"Unknown time unit: {unit}")

def format_time_delta(seconds: int) -> str:
    # Format time delta in seconds to human-readable string.
#
# Args:
# seconds: Time in seconds
#
# Returns:
# Human-readable time string
    if seconds < 60:
        return f"{seconds} сек."
    
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} мин."
    
    hours = minutes // 60
    minutes %= 60
    if hours < 24:
        if minutes == 0:
            return f"{hours} ч."
        return f"{hours} ч. {minutes} мин."
    
    days = hours // 24
    hours %= 24
    if hours == 0:
        return f"{days} д."
    return f"{days} д. {hours} ч."
