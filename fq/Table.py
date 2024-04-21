import json

from .util import is_number


class Table:
    def __init__(self, data: dict):
        self.data = data
        self._stats = None

    @classmethod
    def from_json(cls, json: dict):
        return cls(json)

    @property
    def n_chars(self):
        return len(json.dumps(self.data, ensure_ascii = False, indent = 2))

    @property
    def stats(self):
        if self._stats is None:
            self._stats = TableStats(self)

        return self._stats


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
                        # print(cell_text)
                        n_numeric_cells += 1
                        n_chars_numeric.append(cell_length)
                    elif len(cell_text) < 1:
                        n_empty_cells += 1
                    else:
                        n_text_cells += 1
                        n_chars_text.append(cell_length)

            n_cells += n_cols_current_row_without_placeholders

            if n_cols_current_row > n_cols:
                n_cols = n_cols_current_row

        self.n_cells = n_cells
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.n_chars = n_chars

        self.n_numeric_cells = n_numeric_cells
        self.n_chars_numeric = n_chars_numeric

        self.n_text_cells = n_text_cells
        self.n_chars_text = n_chars_text
        self.n_empty_cells = n_empty_cells
