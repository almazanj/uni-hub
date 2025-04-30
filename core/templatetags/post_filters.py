from django import template
import re

register = template.Library()

@register.filter
def hide_hashtags(text):
    """Remove hashtags from text to avoid duplication with the styled tag display"""
    if text:
        # Replace hashtags with empty string
        return re.sub(r'#\w+', '', text)
    return text