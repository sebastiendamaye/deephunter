from django import template
from urllib.parse import quote
import base64

register = template.Library()

@register.filter
def is_dict(value):
    return isinstance(value, dict)

@register.filter
def encode_url(url):
    """
    Base64 Encode a URL and remove the trailing "=" signs if any
    """
    return base64.urlsafe_b64encode(url.encode()).decode().replace("=", "")
