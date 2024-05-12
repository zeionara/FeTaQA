import os
import re
# import json
from pathlib import Path

from tqdm import tqdm
from docx.api import Document

from .util import normalize_spaces
# from .Cell import Cell
from .Table import Table


PARAGRAPH_SEP_PLACEHOLDER = '__PARAGRAPH_SEP__'
PARAGRAPH_SEP = '\n\n'
TABLE_ID = re.compile('[0-9.]+')
APPLICATION_ID = re.compile('[A-ZА-ЯЁ]+')

DEBUG = False


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

        last_non_empty_paragraph = None

        def is_not_empty(text: str):
            return text is not None and len(text.strip()) > 0

        if first_paragraph_element_after_the_table is None:
            # Find last non-empty paragraph

            for paragraph in paragraphs[::-1]:
                if is_not_empty(paragraph._element.text):
                    last_non_empty_paragraph = paragraph
                    break

            # return None

        i = 0

        context = []
        offset = 0 if first_paragraph_element_after_the_table is None else 1

        title = None
        id_ = None
        is_application = False
        found_reference = False

        for paragraph in paragraphs:
            if (
                first_paragraph_element_after_the_table is None and paragraph._element.text == last_non_empty_paragraph._element.text or
                first_paragraph_element_after_the_table is not None and paragraph._element.text == first_paragraph_element_after_the_table.text
            ):
                while window > 0 and i >= offset:
                    text = paragraphs[i - offset]._element.text

                    if text is not None and len(text.strip()) > 0:
                        normalized_text = text.lower().strip()

                        if id_ is None and normalized_text.startswith('таблица'):
                            title = text

                            for match in TABLE_ID.findall(title):
                                id_ = str(match)
                        elif id_ is None and normalized_text.startswith('приложение'):
                            title = text

                            for match in APPLICATION_ID.findall(title):
                                id_ = str(match)

                            is_application = True
                        else:
                            if id_ is not None and (is_application is False and 'табл' in normalized_text or is_application is True and 'приложен' in normalized_text) and id_ in text:
                                found_reference = True
                                # print('found ref!')
                                # break

                            if found_reference:
                                context.append(text)
                                window -= 1

                    offset += 1

            i += 1

        if len(context) < 1:
            return None

        return normalize_spaces(PARAGRAPH_SEP_PLACEHOLDER.join(context[::-1])).replace(PARAGRAPH_SEP_PLACEHOLDER, PARAGRAPH_SEP)

    def parse_file(self, source: str, get_destination: callable = None):
        document = Document(source)
        # indent = self.json_indent

        if get_destination is None:
            stem = Path(source).stem

            def get_destination(i: int):
                return f'{stem}.{i:04d}'.replace('-', '_') + '.json'

        for i, table in enumerate(document.tables):
            if DEBUG:
                yield Table.from_docx(
                    table,
                    label = (destination := get_destination(i)),
                    context = self.get_context(document, table)
                )
            else:
                try:
                    yield Table.from_docx(
                        table,
                        label = (destination := get_destination(i)),
                        context = self.get_context(document, table)
                    )
                except IndexError:
                    print(f"Can't parse table {destination} due to index error")

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
                get_destination = lambda i: os.path.join(destination, f'{Path(source_file).stem}.{i:04d}'.replace(' ', '_')) + '.json'
            ):
                table.to_json(table.label, indent = indent)
