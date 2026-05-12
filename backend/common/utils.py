import random
import string


def generate_short_code(length):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))
