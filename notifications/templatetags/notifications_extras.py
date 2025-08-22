from django import template

register = template.Library()

@register.filter
def bootstrap_level(level):
    if level == "error":
        return "danger"
    elif level == "debug":
        return "secondary"
    else:
        return level

@register.filter
def fontawesome_level(level):
    if level == "info":
        return "info-circle"
    elif level == "success":
        return "check-circle"
    elif level == "warning":
        return "exclamation-circle"
    elif level == "error":
        return "times-circle"
    elif level == "debug":
        return "bug"
