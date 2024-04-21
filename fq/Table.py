import os
import json

from numpy import percentile


class Table:
    def __init__(self, data: dict):
        self.data = data

    @classmethod
    def from_json(cls, json: dict):
        return cls(json)

    @property
    def n_chars(self):
        return len(json.dumps(self.data, ensure_ascii = False, indent = 2))

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


class Tables:
    def __init__(self, items: list[Table]):
        self._items = items

    @classmethod
    def from_dir(cls, path: str):
        tables = []

        for file in os.listdir(path):
            with open(os.path.join(path, file), 'r') as file:
                tables.append(
                    Table.from_json(
                        json.load(file)
                    )
                )

        return cls(tables)

    @property
    def stats(self):
        return TablesStats(self._items)

    def __iter__(self):
        return self._items


class TablesStats:
    def __init__(self, tables: Tables):
        self.tables = tables

        n_tables = 0

        n_cells_ = []
        n_rows_ = []
        n_cols_ = []
        n_chars_ = []

        total_length = 0

        for table in tables:
            n_tables += 1

            stats = table.stats

            n_rows_.append(stats.n_rows)
            n_cols_.append(stats.n_cols)
            n_cells_.append(stats.n_cells)

            n_chars_.extend(stats.n_chars)

        def print_percentiles(label: str, data: list):
            percentiles = ' '.join(map(''.join, zip(('5%: ', '25%: ', '50%: ', '75%: ', '95%: '), map(lambda value: f'{value:.3f}', percentile(data, (5, 25, 50, 75, 95))))))
            print(f'{label}: {percentiles}')

        print('Number of tables:', n_tables)
        print('Total length:', total_length)

        print_percentiles('Number of cells', n_cells_)
        print_percentiles('Number of rows', n_rows_)
        print_percentiles('Number of columns', n_cols_)
        print_percentiles('Text length', n_chars_)
