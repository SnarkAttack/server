from django import template

register = template.Library()

@register.filter
def get_play_count(value):
    return len(value.all())