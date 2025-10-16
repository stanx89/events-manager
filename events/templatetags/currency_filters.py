from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def currency(value):
    """
    Format a number as currency without dollar sign, with comma separators
    Example: 1234.56 -> 1,234.56
    """
    try:
        # Convert to float if it's a string
        if isinstance(value, str):
            value = float(value)
        
        # Format with comma separator and 2 decimal places
        return f"{value:,.2f}"
    except (ValueError, TypeError):
        return value

@register.filter  
def currency_no_decimal(value):
    """
    Format a number as currency without dollar sign and decimal places if whole number
    Example: 1234.00 -> 1,234 | 1234.56 -> 1,234.56
    """
    try:
        # Convert to float if it's a string
        if isinstance(value, str):
            value = float(value)
        
        # Check if it's a whole number
        if value == int(value):
            return f"{int(value):,}"
        else:
            return f"{value:,.2f}"
    except (ValueError, TypeError):
        return value