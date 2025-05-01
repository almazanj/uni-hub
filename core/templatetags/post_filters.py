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