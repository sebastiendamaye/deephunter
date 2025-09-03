from django import template
from qm.models import Analytic

register = template.Library()

@register.filter
def statuslabel(status):
    return dict(Analytic.STATUS_CHOICES).get(status, status)

@register.filter
def statuscolor(status):
    color= ''
    if status == 'DRAFT':
        color = '#A9C9FF'
    elif status == 'PUB':
        color = '#28A745'
    elif status == 'REVIEW':
        color = '#FFC107'
    elif status == 'PENDING':
        color = '#FF6F00'
    elif status == 'ARCH':
        color = '#6C757D'

    return color
