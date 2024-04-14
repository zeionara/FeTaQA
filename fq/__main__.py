import os
import json
from time import sleep

from click import argument, group, option
# from camelot import read_pdf
from numpy import percentile
# from transformers import pipeline
from tqdm import tqdm
from pathlib import Path
from docx.api import Document

from .util import unpack, normalize_spaces
from .Cell import Cell


@group()
def main():
    pass


class TableTranslator:
    def __init__(self, model: str = 'Helsinki-NLP/opus-mt-ru-en'):
        self.pipeline = pipeline('translation', model = model, framework = 'pt')

    def translate_row(self, row: list[str]):
        return [cell['translation_text'] for cell in self.pipeline(row)]

    def translate(self, table: list[list[str]]):
        translated_table = []

        for row in tqdm(table, desc = 'Translating table'):
            translated_table.append(self.translate_row(row))

        return translated_table


@main.command(name = 'unpack')
@argument('source', type = str)
@argument('destination', type = str, required = False)
def unpack_(source: str, destination: str):
    if destination is None:
        destination = os.path.join('assets', Path(source).stem)

    unpack(source, destination)


@main.command()
@argument('source', type = str)
@argument('destination', type = str)
def parse(source: str, destination: str):
    for source_file in tqdm(os.listdir(source)):
        document = Document(os.path.join(source, source_file))

        if not os.path.isdir(destination):
            os.makedirs(destination)

        for i, table in enumerate(document.tables):
            parsed_rows = []
            destination_file = os.path.join(destination, f'{Path(source_file).stem}.{i}'.replace(' ', '_')) + '.json'

            if os.path.isfile(destination_file):
                continue

            try:
                rows = table.rows
            except:
                print(f'Error when parsing table {i} from file {source_file}. Skipping...')
                continue

            skip_table = False

            for row in rows:
                parsed_cells = []

                try:
                    cells = row.cells
                except:
                    print(f'Error when parsing table {i} from file {source_file}. Skipping...')
                    skip_table = True
                    break

                for cell in cells:
                    # print(dir(cell))
                    # print(cell._element.xml)

                    parsed_cells.append(Cell(normalize_spaces(cell.text)))

                try:
                    parsed_rows.append(Cell.merge_horizontally(parsed_cells))
                except:
                    print(f'Error when merging horizontally on file {source_file}')

            if skip_table:
                continue

            try:
                parsed_rows = Cell.merge_vertically(parsed_rows)
            except:
                print(f'Error when merging vertically on file {source_file}')

            # for row in parsed_rows:
            #     print(row)

            # print(source)

            # print(Cell.serialize_rows(parsed_rows))

            # i = 0


            with open(destination_file, 'w') as file:
                json.dump(Cell.serialize_rows(parsed_rows), file, indent = 2, ensure_ascii = False)


@main.command()
@argument('path', type = str)
@option('--pages', '-p', type = str, default = 'all')
def extract_tables(path: str, pages: str):
    tables = read_pdf(path, pages = pages, flavor = 'lattice')

    # 1. Split rows into cells

    rows = []
    row_lengths = []
    max_source_row_length = 1

    for row in tables[0].data:
        if (source_row_length := len(row)) > max_source_row_length:
            max_source_row_length = source_row_length

        updated_row = row[0].split('\n')

        row_lengths.append(len(updated_row))

        rows.append(updated_row)

    if max_source_row_length < 2:
        # 2. Chose a reasonable number columns

        n_cols = int(percentile(row_lengths, 75))

        # 3. Fold the table rows

        table = []

        for row in rows:
            i = 0
            for cell in row[n_cols:]:
                cell_index = i % n_cols

                row[cell_index] += f' {cell}'
                i += 1

            table.append(row[:n_cols])
    else:
        table = tables[0].data

    for row in table:
        print(row)

    print('Question:')
    question = input('> ')

    print('Answer:')
    answer = input('> ')

    translator = TableTranslator()

    question, answer = translator.translate_row([question, answer])

    # 4. Translate to english

    table = translator.translate(table)

    for row in table:
        print(row)

    print(question)
    print(answer)

    # 5. Make data sample

    sample = {
        "feta_id": 2206,
        "table_source_json": "totto_source/dev_json/example-2205.json",
        "page_wikipedia_url": "http://en.wikipedia.org/wiki/Shagun_Sharma",
        "table_page_title": "Shagun Sharma",
        "table_section_title": "Television",
        "table_array": table,
        "highlighted_cell_ids": [[6, 0], [6, 1], [6, 2], [7, 0], [7, 1], [7, 2], [8, 0], [8, 1], [8, 2]],
        "question": question,
        "answer": answer,
        "source": "mturk-approved"
    }

    print(sample)


if __name__ == '__main__':
    main()
