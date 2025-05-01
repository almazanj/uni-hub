from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter
def hide_hashtags(value):
    """Replaces hashtags with styled spans."""
    if not value:
        return ""
    
    # Pattern to match hashtags
    pattern = r'#(\w+)'
    
    # Replace hashtags with styled spans
    replaced = re.sub(
        pattern, 
        r'<span class="text-indigo-600 font-medium">#\1</span>', 
        value
    )
    
    return mark_safe(replaced)

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