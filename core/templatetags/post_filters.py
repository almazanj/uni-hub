from django import template
import re

register = template.Library()

@register.filter
def hide_hashtags(text):
    """Remove hashtags from text as hashtags are styled elsewhere."""
    if text:
        return re.sub(r'#[\w-]+', '', text)
    return text

@register.filter
def get_item(lst, index):
    """Gets an item from a list at the specified index with modulo operation for cycling."""
    if not lst:
        return ""
        
    items = lst.split(",")
    if not items:
        return ""
        
    # Use modulo to cycle through colors for deeper nesting levels
    return items[int(index) % len(items)]

@register.filter
def is_meaningfully_edited(created_at, updated_at):
    """
    Check if a post has been meaningfully edited with a small threshold
    Returns True only if more than 2 seconds difference
    """
    time_difference = updated_at - created_at
    return time_difference.total_seconds() > 2 

@register.filter
def trim_whitespace(text):
    """Normalize whitespace while preserving intentional line breaks"""
    if not text:
        return text
        
    # Replace multiple consecutive newlines with just two newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Trim leading and trailing whitespace
    text = text.strip()
    
    return text