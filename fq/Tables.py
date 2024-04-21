import os
import json

from numpy import percentile

from .Table import Table


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

        n_cells = []
        n_rows = []
        n_cols = []
        n_chars = []

        total_length = 0

        for table in tables:
            n_tables += 1

            total_length += table.n_chars

            stats = table.stats

            n_rows.append(stats.n_rows)
            n_cols.append(stats.n_cols)
            n_cells.append(stats.n_cells)

            n_chars.extend(stats.n_chars)

        self.n_tables = n_tables
        self.total_length = total_length

        self.n_rows = n_rows
        self.n_cols = n_cols
        self.n_cells = n_cells
        self.n_chars = n_chars

    def print(self):
        def print_percentiles(label: str, data: list):
            percentiles = ' '.join(map(''.join, zip(('5%: ', '25%: ', '50%: ', '75%: ', '95%: '), map(lambda value: f'{value:.3f}', percentile(data, (5, 25, 50, 75, 95))))))
            print(f'{label}: {percentiles}')

        print('Number of tables:', self.n_tables)
        print('Total length:', self.total_length)

        print_percentiles('Number of cells', self.n_cells)
        print_percentiles('Number of rows', self.n_rows)
        print_percentiles('Number of columns', self.n_cols)
        print_percentiles('Text length', self.n_chars)
