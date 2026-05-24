import os
import random
import string
from io import BytesIO

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from common.constants import SHOPPING_LIST_TEXT


def generate_short_code(length):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


def build_txt(ingredients):
    lines = [f'{SHOPPING_LIST_TEXT}:\n']

    for ing in ingredients:
        lines.append(
            f'{ing["ingredient__name"]}: '
            f'{ing["total_amount"]} '
            f'{ing["ingredient__measurement_unit"]}.'
        )

    return '\n'.join(lines)


def build_pdf(ingredients):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)

    font_path = os.path.join('static', 'fonts', 'arial.ttf')
    pdfmetrics.registerFont(TTFont('arial', font_path))

    y = 800
    p.setFont('Arial', 16)
    p.drawString(100, y, SHOPPING_LIST_TEXT)
    y -= 30

    p.setFont('Arial', 12)
    for ing in ingredients:
        line = (
            f'{ing["ingredient__name"]}: '
            f'{ing["total_amount"]} '
            f'{ing["ingredient__measurement_unit"]}.'
        )

        p.drawString(100, y, line)
        y -= 20

        if y < 50:
            p.showPage()
            p.setFont('Arial', 12)
            y = 800

    p.save()
    buffer.seek(0)
    return buffer
