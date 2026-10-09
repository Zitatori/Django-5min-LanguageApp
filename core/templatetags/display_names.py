import re
from django import template

register = template.Library()


@register.filter
def has_generated_username(user):
    return bool(re.fullmatch(r'member_[0-9a-f]{32}', getattr(user, 'username', '')))


@register.filter
def display_name(user):
    username = getattr(user, 'username', '')
    if re.fullmatch(r'member_[0-9a-f]{32}', username):
        return user.first_name or 'Member'
    return username
