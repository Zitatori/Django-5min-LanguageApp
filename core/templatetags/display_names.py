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


@register.filter
def level_label(value):
    from django.utils.translation import gettext as _
    descriptions = {
        'A1': _('Beginner: basic greetings and introductions'),
        'A2': _('Simple exchanges on familiar topics'),
        'B1': _('Can hold everyday conversations'),
        'B2': _('Can discuss varied topics and explain opinions'),
        'C1': _('Near-native fluency'),
        'C2': _('Vocabulary beyond native-speaker level'),
    }
    if value not in descriptions:
        return value or ''
    return '{} ({})'.format(value, descriptions[value])
