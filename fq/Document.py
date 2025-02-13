from dataclasses import dataclass

from .Paragraph import Paragraph
from .Table import Table


@dataclass
class Document:
    items: list[Paragraph | Table]

    @property
    def tables(self):
        items = []

        for table in self.items:
            if table.type_label == Table.type_label:
                items.append(table)

        return items

    @property
    def paragraphs(self):
        items = []

        for paragraph in self.items:
            if paragraph.type_label == Paragraph.type_label:
                items.append(paragraph)

        return items
