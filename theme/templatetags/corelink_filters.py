from django import template

register = template.Library()

GRADIENTS = [
    'linear-gradient(135deg,#0A66C2,#06B6D4)',
    'linear-gradient(135deg,#7C3AED,#D946EF)',
    'linear-gradient(135deg,#059669,#06B6D4)',
    'linear-gradient(135deg,#D97706,#f59e0b)',
    'linear-gradient(135deg,#dc2626,#f43f5e)',
]

@register.filter
def avatar_gradient(value):
    """Return a deterministic gradient based on the counter value."""
    if value is None:
        value = 0
    return GRADIENTS[int(value) % len(GRADIENTS)]
