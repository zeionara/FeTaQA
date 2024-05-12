import json


class Table:
    def __init__(self, data: dict):
        self.data = data

    @classmethod
    def from_json(cls, json: dict):
        return cls(json)

    @property
    def n_chars(self):
        return len(json.dumps(self._json, ensure_ascii = False, indent = 2))

    @property
    def stats(self):
        return TableStats(self)


class TableStats:
    def __init__(self, table: Table):
        self._item = table

        n_cells = 0
        n_rows = 0
        n_cols = 0
        n_chars = []

        for row in table.data['rows']:
            n_rows += 1

            n_cols_current_row = 0
            n_cols_current_row_without_placeholders = 0

            for cell in row:
                n_cols_current_row += 1

                if (cell_text := cell.get('text')) is not None:
                    n_cols_current_row_without_placeholders += 1
                    n_chars.append(len(cell_text))

            n_cells += n_cols_current_row_without_placeholders

            if n_cols_current_row > n_cols:
                n_cols = n_cols_current_row

        self.n_cells = n_cells
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.n_chars = n_chars
