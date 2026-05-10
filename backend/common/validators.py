import re

from django.core.validators import RegexValidator
from rest_framework.exceptions import ValidationError

from common.constants import SLUG_REGEX, USERNAME_REGEX


def validate_username(value):
    if value.lower() == 'me':
        raise ValidationError(
            'Имя пользователя "me" запрещено'
        )

    forbidden_chars = re.sub(USERNAME_REGEX, '', value)
    if forbidden_chars:
        raise ValidationError(
            'В имени пользователя запрещены символы: '
            f'{", ".join(sorted(set(forbidden_chars)))}'
        )

    return value

slug_validator = RegexValidator(
    regex=SLUG_REGEX,
    message='Здесь разрешены только латинские буквы, цифры, дефис и '
            'подчёркивание'
)
