import re

SPACE = re.compile(r'\s+')
APOS = re.compile(r'\s*&apos;\s*')


def normalize_spaces(string: str):
    return SPACE.sub(' ', string).strip()


def unescape_translation(string: str):
    return APOS.sub("'", string)
