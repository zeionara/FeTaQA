from __future__ import annotations

import uuid


class Cell:
    def __init__(self, text: str, n_rows = 1, n_cols = 1):
        self.text = text

        self.n_rows = n_rows
        self.n_cols = n_cols

        self._id = None

    def increment_n_rows(self):
        self.n_rows += 1

    @property
    def id(self):
        if self._id is None:
            self._id = str(uuid.uuid4())

        return self._id

    @classmethod
    def merge_horizontally(cls, row: list[Cell]):
        merged_row = []

        current_text = None
        current_group = None

        for cell in row:
            if current_text is None:
                current_text = cell.text
                current_group = [cell]
            elif cell.text == current_text:
                current_group.append(cell)
            else:
                merged_row.append(cls(current_text, n_rows = 1, n_cols = len(current_group)))

                current_text = cell.text
                current_group = [cell]

        if current_group is not None:
            merged_row.append(cls(current_text, n_rows = 1, n_cols = len(current_group)))

        return merged_row

    @classmethod
    def merge_vertically(cls, rows: list[list[Cell]]):
        # for row in rows:
        #     print('>>', rows)

        merged_rows = []

        last_row = None

        last_row_offset = None
        current_row_offset = None

        for row in rows:
            merged_row = []

            if last_row is None:
                last_row = row
                merged_rows.append(row)
                continue

            last_row_offset = 0
            current_row_offset = 0
            last_row_index = 0

            for cell in row:
                # print(row, last_row, last_row_index)
                # print(cell.text, last_row[last_row_index].text)
                last_row_cell = last_row[last_row_index] if last_row_index < len(last_row) else None

                if last_row_cell is not None and last_row_cell == cell and last_row_offset == current_row_offset:
                    merged_row.append(last_row_cell.make_placeholder())
                    last_row_cell.increment_n_rows()
                else:
                    merged_row.append(cell)

                current_row_offset += cell.n_cols

                if last_row_cell is not None:
                    last_row_offset += last_row_cell.n_cols

                last_row_index += 1

            merged_rows.append(merged_row)
            last_row = merged_row

        return merged_rows

    def __repr__(self):
        return f'{self.text} {self.n_rows}x{self.n_cols}'

    def __eq__(lhs, rhs):
        # return lhs.text == rhs.text and lhs.n_rows == rhs.n_rows and lhs.n_cols == rhs.n_cols
        return lhs.text == rhs.text and lhs.n_cols == rhs.n_cols

    def make_placeholder(self):
        return Placeholder(origin = self)

    def serialize(self):
        return {
            'id': self.id,
            'text': self.text,
            'rows': self.n_rows,
            'cols': self.n_cols
        }

    @staticmethod
    def serialize_rows(rows: list[list[Cell]], context: str = None, title: str = None, id_: str = None):
        data = {
            'rows': [
                [
                    cell.serialize()
                    for cell in row
                ]
                for row in rows
            ]
        }

        if context is not None:
            data['context'] = context

        if title is not None:
            data['title'] = title

        if id_ is not None:
            data['id'] = id_

        return data


class Placeholder:
    def __init__(self, origin: Cell):
        self.origin = origin

    def __eq__(lhs, rhs):
        return lhs.origin == rhs

    def increment_n_rows(self):
        return self.origin.increment_n_rows()

    def make_placeholder(self):
        return self

    @property
    def text(self):
        return None

    @property
    def n_rows(self):
        return self.origin.n_rows

    @property
    def n_cols(self):
        return self.origin.n_cols

    def serialize(self):
        return {
            'id': self.origin.id
        }

    def __repr__(self):
        return f'{self.origin.text} {self.n_rows}x{self.n_cols}'
