import json
from typing import ClassVar
import re

from numpy import mean
from docx.table import Table as TableDocx
from bs4 import BeautifulSoup

from .util import is_number, drop_space_around_punctuation, normalize_spaces, is_bold
from .Cell import Cell
from .Item import Item
from .TableType import TableType


NOTE_PATTERN = re.compile(r'([*]+)\s+([^*]+[^*\s])')


def get_aligned_cell(cells: list[Cell], col_offset: int):
    n_cols = 0

    for cell in cells:
        if col_offset <= n_cols:
            return cell

        n_cols += cell.n_cols

    return cell


class Table(Item):
    type_label: ClassVar[str] = 'table'

    def __init__(self, data: dict, label: str):
        self.data = data
        self.label = label
        self._stats = None

        self.contexts = None

    @classmethod
    def from_json(cls, json: dict, label: str):
        return cls(json, label)

    @classmethod
    def from_docx(cls, table: TableDocx, label: str, title: str = None, id_: str = None, table_type: TableType = None, context: str = None):
        parsed_rows = []

        for row in table.rows:
            parsed_cells = []

            for cell in row.cells:
                parsed_cells.append(Cell(normalize_spaces(cell.text)))

            parsed_rows.append(Cell.merge_horizontally(parsed_cells))

        parsed_rows = Cell.merge_vertically(parsed_rows)

        return cls(Cell.serialize_rows(parsed_rows, context, title, id_, table_type), label)

    @classmethod
    def from_soup(cls, soup: BeautifulSoup, label: str, title: str = None, id_: str = None, table_type: TableType = None, context: str = None):
        rows = []
        last_row = None
        bold_text = [] if title is None else None

        if bold_text is not None:
            for fragment in soup.find_all('w:r'):
                if is_bold(fragment):
                    bold_text.append(fragment.text)

            title = normalize_spaces(' '.join(bold_text))

            if title.endswith(':'):
                title = title[:-1]

        for row in soup.find_all('w:tr'):
            cells = []

            col_offset = 0

            for cell in row.find_all('w:tc'):

                if last_row is not None and (vertical_span := cell.find('w:vmerge')) is not None and vertical_span.get('w:val') != 'restart':
                    cells.append(
                        placeholder := get_aligned_cell(last_row, col_offset).make_placeholder()
                    )

                    (origin := placeholder.origin).n_rows += 1
                    col_offset += origin.n_cols
                else:
                    n_cols = 1

                    if (horizontal_span := cell.find('w:gridspan')) is not None and (span_size := horizontal_span.get('w:val')) is not None:
                        n_cols = int(span_size)

                    col_offset += n_cols

                    cells.append(
                        Cell(
                            drop_space_around_punctuation(
                                normalize_spaces(cell.text)
                            ),
                            n_cols = n_cols
                        )
                    )

            last_row = cells
            rows.append(cells)

        # Parse notes - just add the note text in brackets after the original cell content without removing the anchor symbol(s)

        notes = {}

        # if rows[0][0].text.startswith('Сооружения'):

        for row in rows:
            for cell in row:
                if cell.text is not None:
                    for note in NOTE_PATTERN.findall(cell.text):
                        notes[note[0]] = note[1]

        for row in rows:
            for cell in row:
                for key in sorted(notes.keys(), key = lambda key: len(key), reverse = True):
                    if cell.text is not None and cell.text.endswith(key):
                        # cell.text = f'{cell.text.strip()[:-(len(key) + 2)]} ({value})'
                        cell.text = normalize_spaces(f'{cell.text} ({notes[key]})')

        return cls(Cell.serialize_rows(rows, context, title, id_, table_type), label)

    def to_json(self, path: str, indent: int):
        with open(path, 'w') as file:
            json.dump(self.data, file, indent = indent, ensure_ascii = False)

    @property
    def json(self):
        context = self.context

        data = self.data

        if context is not None:
            data['context'] = context.json

        return data

    @property
    def n_chars(self):
        return len(json.dumps(self.data, ensure_ascii = False, indent = 2))

    @property
    def stats(self):
        if self._stats is None:
            self._stats = TableStats(self)

        return self._stats

    @property
    def context(self):
        return self.data.get('context')

    @property
    def type(self):
        return self.data.get('type')

    @property
    def content(self):
        return [
            [
                cell.get('text')
                for cell in row
            ]
            for row in self.data['rows']
        ]

    @property
    def next_sibling_paragraphs(self):
        soup = self.data.get('soup')

        return None if soup is None else soup.findNextSiblings('w:p')

    @property
    def previous_sibling_paragraphs(self):
        soup = self.data.get('soup')

        return None if soup is None else soup.findPreviousSiblings('w:p')

    @property
    def next_sibling_paragraph(self):
        for item in self.next_sibling_paragraphs:
            if (text := item.text) is not None and len(text.strip()) > 0:
                return item

    @property
    def previous_sibling_paragraph(self):
        for item in self.previous_sibling_paragraphs:
            if (text := item.text) is not None and len(text.strip()) > 0:
                return item

    @property
    def title(self):
        return self.data.get('title')

    @property
    def id(self):
        return self.data.get('id')

    @property
    def isotropic(self):
        row_length = None

        for row in self.data['rows']:
            if row_length is None:
                row_length = len(row)
                continue

            if len(row) != row_length or any(cell.get('text') is None for cell in row):
                return False

        return True

    @property
    def as_text(self):
        if not self.isotropic:
            raise ValueError("Can't convert non-isotropic table into text")

        data = self.data

        lines = [] if (title := data.get('title')) is None else [title]

        for row in self.data['rows']:
            lines.append(' '.join(cell['text'] for cell in row))

        return '\n'.join(lines)


class TableStats:
    def __init__(self, table: Table):
        self._item = table

        n_cells = 0
        n_rows = 0
        n_cols = 0
        n_chars = []

        n_numeric_cells = 0
        n_text_cells = 0
        n_empty_cells = 0

        n_chars_numeric = []
        n_chars_text = []

        n_rowspans = []
        n_colspans = []

        for row in table.data['rows']:
            n_rows += 1

            n_cols_current_row = 0
            n_cols_current_row_without_placeholders = 0

            for cell in row:
                n_cols_current_row += 1

                if (cell_text := cell.get('text')) is not None:
                    n_cols_current_row_without_placeholders += 1
                    n_chars.append(cell_length := len(cell_text))

                    if is_number(cell_text):
                        n_numeric_cells += 1
                        n_chars_numeric.append(cell_length)
                    elif len(cell_text) < 1:
                        n_empty_cells += 1
                    else:
                        n_text_cells += 1
                        n_chars_text.append(cell_length)

                    n_rowspans.append(cell.get('rows'))
                    n_colspans.append(cell.get('cols'))

            n_cells += n_cols_current_row_without_placeholders

            if n_cols_current_row > n_cols:
                n_cols = n_cols_current_row

        # print(n_cells)

        self.n_cells = n_cells
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.n_chars = n_chars

        self.n_numeric_cells = n_numeric_cells
        self.n_chars_numeric = n_chars_numeric

        self.n_text_cells = n_text_cells
        self.n_chars_text = n_chars_text
        self.n_empty_cells = n_empty_cells

        self.n_rowspans = n_rowspans
        self.n_colspans = n_colspans

    @property
    def as_vector(self):
        return [
            self.n_cells,
            self.n_rows,
            self.n_cols,
            sum(self.n_chars), 0 if len(self.n_chars) < 1 else mean(self.n_chars),
            self.n_numeric_cells,
            self.n_text_cells,
            self.n_empty_cells,
            sum(self.n_chars_numeric), 0 if len(self.n_chars_numeric) < 1 else mean(self.n_chars_numeric),
            sum(self.n_chars_text), 0 if len(self.n_chars_text) < 1 else mean(self.n_chars_text),
            self.mean_rowspan,
            self.mean_colspan
        ]

    @classmethod
    @property
    def vector_legend(self):
        return [
            'n-cells',
            'n-rows',
            'n-cols',
            'n-chars-sum', 'n-chars-mean',
            'n-numeric-cells',
            'n-text-cells',
            'n-empty-cells',
            'n-chars-numeric-sum', 'n-chars-numeric-mean',
            'n-chars-text-sum', 'n-chars-text-mean',
            'mean-rowspan',
            'mean-colspan'
        ]

    @property
    def mean_rowspan(self):
        return 0 if len(self.n_rowspans) < 1 else mean(self.n_rowspans)

    @property
    def mean_colspan(self):
        return 0 if len(self.n_colspans) < 1 else mean(self.n_colspans)
