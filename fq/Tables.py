from __future__ import annotations

import os
import json

from numpy import percentile

from .Table import Table


class Tables:
    def __init__(self, items: list[Table], base: Tables = None):
        self._base = base
        self._items = items
        self._stats = None

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
        if self._stats is None:
            self._stats = TablesStats(self._items, None if self._base is None else self._base.stats)

        return self._stats

    @property
    def non_trivial(self):
        return Tables(
            [item for item in self._items if item.stats.n_cells > 1 and item.stats.n_rows > 1 and item.stats.n_cols > 1],
            base = self if self._base is None else self._base
        )

    def __iter__(self):
        return self._items


class TablesStats:
    def __init__(self, tables: Tables, base_stats: TablesStats = None):
        self._base_stats = base_stats

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

    @property
    def total_length_as_str(self):
        return f'{self.total_length:_}'.replace('_', ' ')

    def print(self):
        def print_percentiles(label: str, data: list):
            percentiles = ' '.join(map(''.join, zip(('5%: ', '25%: ', '50%: ', '75%: ', '95%: '), map(lambda value: f'{value:.1f}', percentile(data, (5, 25, 50, 75, 95))))))
            print(f'{label}: {percentiles}')

        if self._base_stats is None:
            print('Number of tables:', self.n_tables)
        else:
            print(f'Number of tables: {self.n_tables} / {self._base_stats.n_tables} ({self.n_tables / self._base_stats.n_tables * 100:.3f}%)')

        if self._base_stats is None:
            print('Total length:', self.total_length)
        else:
            print(f'Total length: {self.total_length_as_str} / {self._base_stats.total_length_as_str} ({self.total_length / self._base_stats.total_length * 100:.3f}%)')

        print_percentiles('Number of cells', self.n_cells)
        print_percentiles('Number of rows', self.n_rows)
        print_percentiles('Number of columns', self.n_cols)
        print_percentiles('Text length', self.n_chars)
