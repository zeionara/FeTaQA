import re

NUMBER_TEMPLATE = re.compile(r'(?:[^\w]|[0-9])+')


def is_number(string: str):
    return NUMBER_TEMPLATE.fullmatch(string)
