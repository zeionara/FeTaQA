import os
# import json
from pathlib import Path

from tqdm import tqdm
from docx.api import Document

from .util import normalize_spaces
# from .Cell import Cell
from .Table import Table


PARAGRAPH_SEP_PLACEHOLDER = '__PARAGRAPH_SEP__'
PARAGRAPH_SEP = '\n\n'


class Parser:
    def __init__(self, context_window_size: int = 5, json_indent: int = 2):
        self.context_window_size = context_window_size
        self.json_indent = json_indent

    def get_context(self, document, table):
        window = self.context_window_size

        paragraphs = document.paragraphs

        first_paragraph_element_after_the_table = None

        for item in table._element.itersiblings():
            if (text := item.text) is not None and len(text.strip()) > 0:
                first_paragraph_element_after_the_table = item
                break

        if first_paragraph_element_after_the_table is None:
            return None

        i = 0

        context = []
        offset = 1

        for paragraph in paragraphs:
            if paragraph._element.text == first_paragraph_element_after_the_table.text:
                while window > 0:
                    text = paragraphs[i - offset]._element.text

                    if text is not None and len(text.strip()) > 0:
                        context.append(text)

                        if not text.startswith('Таблица'):
                            window -= 1

                    offset += 1

            i += 1

        return normalize_spaces(PARAGRAPH_SEP_PLACEHOLDER.join(context[::-1])).replace(PARAGRAPH_SEP_PLACEHOLDER, PARAGRAPH_SEP)

    def parse_file(self, source: str, get_destination: callable):
        document = Document(source)
        # indent = self.json_indent

        for i, table in enumerate(document.tables):
            yield Table.from_docx(
                table,
                label = get_destination(i),
                context = self.get_context(document, table)
            )

        # for i, table in enumerate(document.tables):
        #     context = self.get_context(document, table)

        #     if context is None:
        #         print(f'No context for table {i} in file {source}')

        #     parsed_rows = []
        #     destination = get_destination(i)

        #     if os.path.isfile(destination):
        #         continue

        #     try:
        #         rows = table.rows
        #     except:
        #         print(f'Error when parsing table {i} from file {source}. Skipping...')
        #         continue

        #     skip_table = False

        #     for row in rows:
        #         parsed_cells = []

        #         try:
        #             cells = row.cells
        #         except:
        #             print(f'Error when parsing table {i} from file {source}. Skipping...')
        #             skip_table = True
        #             break

        #         for cell in cells:
        #             parsed_cells.append(Cell(normalize_spaces(cell.text)))

        #         try:
        #             parsed_rows.append(Cell.merge_horizontally(parsed_cells))
        #         except:
        #             print(f'Error when merging horizontally on file {source}')

        #     if skip_table:
        #         continue

        #     try:
        #         parsed_rows = Cell.merge_vertically(parsed_rows)
        #     except:
        #         print(f'Error when merging vertically on file {source}')

        #     with open(destination, 'w') as file:
        #         json.dump(Cell.serialize_rows(parsed_rows, context), file, indent = indent, ensure_ascii = False)

    def parse(self, source: str, destination: str):
        indent = self.json_indent

        if not os.path.isdir(destination):
            os.makedirs(destination)

        for source_file in tqdm(os.listdir(source)):
            for table in self.parse_file(
                source = os.path.join(source, source_file),
                get_destination = lambda i: os.path.join(destination, f'{Path(source_file).stem}.{i}'.replace(' ', '_')) + '.json'
            ):
                table.to_json(table.label, indent = indent)
