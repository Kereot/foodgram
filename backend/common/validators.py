import re

from rest_framework.exceptions import ValidationError

from common.constants import USERNAME_REGEX


def validate_username(value):
    forbidden_chars = re.sub(USERNAME_REGEX, '', value)
    if forbidden_chars:
        raise ValidationError(
            'В имени пользователя запрещены символы: '
            f'{", ".join(sorted(set(forbidden_chars)))}'
        )

    return value


def validate_required_field(field, attrs):
    if field not in attrs or not attrs[field]:
        raise ValidationError(
            {field: f'Для данного запроса поле {field} обязательно.'}
        )


def validate_unique_field(field, attrs, is_nested=False):
    data = attrs.get(field, [])
    if is_nested:
        nested_data = []
        for item in data:
            nested_item = item.get('id')
            if not nested_item:
                raise ValidationError(
                    {field: f'У вложенного в {field} поля пустое значение.'}
                )
            nested_data.append(nested_item)
        data = nested_data

    if len(set(data)) != len(data):
        raise ValidationError(
            {field: f'Значения полей {field} не должны повторяться.'}
        )
