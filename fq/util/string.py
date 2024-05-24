import re

SPACE = re.compile(r'\s+')
APOS = re.compile(r'\s*&apos;\s*')

PUNCTUATION_WITH_LEADING_SPACE = re.compile(r'\s+([.,;])')
PUNCTUATION_WITH_TRAILING_SPACE = re.compile(r'([\[])\s+')


def normalize_spaces(string: str):
    return SPACE.sub(' ', string).strip()


def unescape_translation(string: str):
    return APOS.sub("'", string)


def count_dots(string: str):
    n_dots = 0

    for c in string:
        if c == '.':
            n_dots += 1

    return n_dots


def has_not_fewer_dots_than(lhs: str, rhs: str):
    return count_dots(lhs) >= count_dots(rhs)


def drop_space_around_punctuation(string: str):
    return PUNCTUATION_WITH_TRAILING_SPACE.sub(
        r'\g<1>',
        PUNCTUATION_WITH_LEADING_SPACE.sub(r'\g<1>', string)
    )


def is_not_empty(text: str):
    return text is not None and len(text.strip()) > 0
