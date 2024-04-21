from __future__ import annotations

import os
import json

from numpy import percentile, mean
from pandas import DataFrame

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

        n_numeric_cells = []
        n_text_cells = []
        n_empty_cells = []

        n_chars_numeric = []
        n_chars_text = []

        n_rowspans = []
        n_colspans = []

        mean_rowspans = []
        mean_colspans = []

        for table in tables:
            n_tables += 1

            total_length += table.n_chars

            stats = table.stats

            n_rows.append(stats.n_rows)
            n_cols.append(stats.n_cols)
            n_cells.append(stats.n_cells)

            n_chars.extend(stats.n_chars)

            n_numeric_cells.append(stats.n_numeric_cells)
            n_text_cells.append(stats.n_text_cells)
            n_empty_cells.append(stats.n_empty_cells)

            n_chars_numeric.extend(stats.n_chars_numeric)
            n_chars_text.extend(stats.n_chars_text)

            n_rowspans.extend(stats.n_rowspans)
            n_colspans.extend(stats.n_colspans)

            mean_rowspans.append(stats.mean_rowspan)
            mean_colspans.append(stats.mean_colspan)

        self.n_tables = n_tables
        self.total_length = total_length

        self.n_rows = n_rows
        self.n_cols = n_cols
        self.n_cells = n_cells
        self.n_chars = n_chars

        self.n_numeric_cells = n_numeric_cells
        self.n_text_cells = n_text_cells
        self.n_empty_cells = n_empty_cells

        self.n_chars_numeric = n_chars_numeric
        self.n_chars_text = n_chars_text

        self.n_rowspans = n_rowspans
        self.n_colspans = n_colspans

        self.mean_rowspans = mean_rowspans
        self.mean_colspans = mean_colspans

    @property
    def total_length_as_str(self):
        return f'{self.total_length:_}'.replace('_', ' ')

    @property
    def n_cells_sum(self):
        return sum(self.n_cells)

    @property
    def n_numeric_cells_sum(self):
        return sum(self.n_numeric_cells)

    @property
    def n_text_cells_sum(self):
        return sum(self.n_text_cells)

    @property
    def n_empty_cells_sum(self):
        return sum(self.n_empty_cells)

    def print(self):
        # def print_percentiles(label: str, data: list):
        #     percentiles = ' '.join(map(''.join, zip(('5%: ', '25%: ', '50%: ', '75%: ', '95%: '), map(lambda value: f'{value:.1f}', percentile(data, (5, 25, 50, 75, 95))))))
        #     print(f'{label}: {percentiles}')

        def add_percentiles(label: str, data: list, accumulator: dict = None):
            if accumulator is None:
                accumulator = {}

            accumulator[label] = {
                key: value
                for key, value in
                zip(('5%', '25%', '50%', '75%', '95%'), map(lambda value: f'{value:.1f}', percentile(data, (5, 25, 50, 75, 95))))
            }

            return accumulator

        if self._base_stats is None:
            print('Number of tables:', self.n_tables)
        else:
            print(f'Number of tables: {self.n_tables} / {self._base_stats.n_tables} ({self.n_tables / self._base_stats.n_tables * 100:.3f}%)')

        if self._base_stats is None:
            print('Total length:', self.total_length)
        else:
            print(f'Total length: {self.total_length_as_str} / {self._base_stats.total_length_as_str} ({self.total_length / self._base_stats.total_length * 100:.3f}%)')

        print()

        if self._base_stats is None:
            raise NotImplementedError()
        else:
            print(f'N numeric cells: {self.n_numeric_cells_sum} / {self.n_cells_sum} ({self.n_numeric_cells_sum / self.n_cells_sum * 100:.3f}%)')
            print(f'N text cells: {self.n_text_cells_sum} / {self.n_cells_sum} ({self.n_text_cells_sum / self.n_cells_sum * 100:.3f}%)')
            print(f'N empty cells: {self.n_empty_cells_sum} / {self.n_cells_sum} ({self.n_empty_cells_sum / self.n_cells_sum * 100:.3f}%)')

        # print_percentiles('Number of cells', self.n_cells)
        # print_percentiles('Number of rows', self.n_rows)
        # print_percentiles('Number of columns', self.n_cols)
        # print_percentiles('Text length', self.n_chars)

        stats = add_percentiles(
            'Mean colspan', self.mean_colspans,
            add_percentiles(
                'Mean rowspan', self.mean_rowspans,
                add_percentiles(
                    'Colspan', self.n_colspans,
                    add_percentiles(
                        'Rowspan', self.n_rowspans,
                        add_percentiles(
                            'Text cell length', self.n_chars_text,
                            add_percentiles(
                                'Numeric cell length', self.n_chars_numeric,
                                add_percentiles(
                                    'Number of text cells', self.n_text_cells,
                                    add_percentiles(
                                        'Number of numeric cells', self.n_numeric_cells,
                                        add_percentiles(
                                            'Text length', self.n_chars,
                                            add_percentiles(
                                                'Number of columns', self.n_cols,
                                                add_percentiles(
                                                    'Number of rows', self.n_rows,
                                                    add_percentiles('Number of cells', self.n_cells)
                                                )
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )
        )

        df = DataFrame.from_dict(stats, orient = 'index')

        print()
        print(df)
