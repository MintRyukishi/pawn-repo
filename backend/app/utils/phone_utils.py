# backend/app/utils/phone_utils.py
import re

def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number by removing all non-digit characters
    and keeping only the last 10 digits for North American numbers
    """
    if not phone:
        return phone
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # For North American numbers, keep last 10 digits
    # This handles +1 country code
    if len(digits_only) == 11 and digits_only.startswith('1'):
        return digits_only[-10:]
    elif len(digits_only) == 10:
        return digits_only
    else:
        # Return as-is for other formats
        return digits_only

def format_phone_display(phone: str) -> str:
    """
    Format phone number for display as XXX-XXX-XXXX
    """
    normalized = normalize_phone_number(phone)
    if len(normalized) == 10:
        return f"{normalized[:3]}-{normalized[3:6]}-{normalized[6:]}"
    return phone