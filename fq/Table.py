import json

from numpy import mean
from docx.table import Table as TableDocx

from .util import is_number
from .Cell import Cell
from .util import normalize_spaces


class Table:
    def __init__(self, data: dict, label: str):
        self.data = data
        self.label = label
        self._stats = None

    @classmethod
    def from_json(cls, json: dict, label: str):
        return cls(json, label)

    @classmethod
    def from_docx(cls, table: TableDocx, label: str, context: str, title: str, id_: str):
        parsed_rows = []

        for row in table.rows:
            parsed_cells = []

            for cell in row.cells:
                parsed_cells.append(Cell(normalize_spaces(cell.text)))

            parsed_rows.append(Cell.merge_horizontally(parsed_cells))

        parsed_rows = Cell.merge_vertically(parsed_rows)

        return cls(Cell.serialize_rows(parsed_rows, context, title, id_), label)

    def to_json(self, path: str, indent: int):
        with open(path, 'w') as file:
            json.dump(self.data, file, indent = indent, ensure_ascii = False)

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
