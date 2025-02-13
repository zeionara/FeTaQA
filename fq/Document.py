from dataclasses import dataclass

from .Paragraph import Paragraph
from .Table import Table


@dataclass
class Document:
    items: list[Paragraph | Table]
