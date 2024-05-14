import re

SPACE = re.compile(r'\s+')
APOS = re.compile(r'\s*&apos;\s*')


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
