from typing import ClassVar

from dataclasses import dataclass


@dataclass
class Item:
    type_label: ClassVar[str] = None

    content: str | list[str]
