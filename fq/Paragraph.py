from json import dump
from typing import ClassVar

from bs4 import BeautifulSoup

from .util import normalize_spaces, get_paragraph_style, is_bold
from .Cell import ReferentiableObject
from .Item import Item


INCLUDE_XML = False
INDENT = 2


class Paragraph(ReferentiableObject, Item):
    type_label: ClassVar[str] = 'paragraph'

    def __init__(self, soup: BeautifulSoup, text: str, style: str, bold: bool, id_: str = None):
        self.soup = soup
        self.text = text

        self.style = style
        self.bold = bold

        super().__init__(id_)

    @classmethod
    def from_soup(cls, soup: BeautifulSoup):
        if not soup.text:
            return None

        return cls(
            soup,
            text = normalize_spaces(soup.text),
            style = get_paragraph_style(soup),
            bold = is_bold(soup)
        )

    @property
    def content(self):
        return self.text

    def to_json(self, path: str = None, indent: int = INDENT):
        data = {
            'type': self.type_label,
            'id': self.id,
            'text': self.text,
            'style': self.style,
            'bold': self.bold
        }

        if INCLUDE_XML:
            data['xml'] = str(self.soup)

        if path is not None:
            with open(path, 'w', encoding = 'utf-8') as file:
                dump(data, file, indent = indent, ensure_ascii = False)

        return data

    @property
    def json(self):
        return self.to_json()
