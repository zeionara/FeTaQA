import os
from os import environ as env
import json
# from time import sleep

from click import argument, group, option
from numpy import percentile
from tqdm import tqdm
from pathlib import Path
from docx.api import Document
from requests import post
# from camelot import read_pdf

from .util import unpack, normalize_spaces, is_number
from .Cell import Cell
from .Tables import Tables
# from .TableTranslator import TableTranslator


@group()
def main():
    pass


BARD_API_KEY = env.get('BARD_API_KEY')

QUESTION_GENERATION_TASK_DESCRIPTION = (
    'There is a table represented as a nested python list. The outer list corresponds to the list of rows, and the inner lists correspond to the lists of cells for each row. '
    'For each cell there is a number of columns which the cell spans represented by property "cols" and the number of spanned rows represented by property "rows". '
    'If cell spans multiple rows, only entry for the topmost row is filled with the cell content, the cell occurrences on other rows are replaced with a placeholder, '
    'which refers to the anchor entry using the attribute "id". Your task is to generate a question-answer pair based on information provided in this table. '
    'In other words, you should generate a question which may be answered using only information presented in this table, and provide the correct answer. '
    'The question must not be about table structure, but about table content. '
    'Please, precede the generated question with prefix "QUESTION: " and precede the correct answer with prefix "ANSWER: "'
)
QUESTION_GENERATION_PROMPT = '{task}\n\nTABLE: {table}'


# print(len(QUESTION_GENERATION_TASK_DESCRIPTION))


@main.command()
@argument('path', type = str)
def make_questions(path: str):
    with open(path, 'r') as file:
        table = json.load(file)

    prompt = QUESTION_GENERATION_PROMPT.format(
        task = QUESTION_GENERATION_TASK_DESCRIPTION,
        table = json.dumps(table['rows'], ensure_ascii = False, indent = 2)
    )

    # print(prompt)

    response = post(
        'https://api.mistral.ai/v1/chat/completions',
        json = {
            'model': 'mistral-small-latest',
            'messages': [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            # "temperature": 0.7,
            # "top_p": 1
            # "max_tokens": 512,
            # "stream": False,
            # "safe_prompt": False,
            # "random_seed": 17
        }
    )

    print(response.json())

    # response = post(
    #     'http://normax:8000/v1/chat/completions',
    #     json = {
    #         'model': 'openchat_3.5',
    #         'messages': [
    #             {
    #                 'role': 'user',
    #                 'content': prompt
    #             }
    #         ]
    #     }
    # )

    # print(response.json()['choices'][0]['message']['content'])

    # http_proxy = FreeProxy(country_id = 'US', https = True).get()
    # https_proxy = FreeProxy(country_id = 'US', https = True).get()

    # https_proxy = 'https://54.212.22.168:1080'

    # print('got proxy')

    # response = post(
    #     f'https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={BARD_API_KEY}',
    #     json = {
    #         'contents': [
    #             {
    #                 'role': 'user',
    #                 'parts': [
    #                     {
    #                         'text': 'Give me five subcategories of jazz?'
    #                     }
    #                 ]
    #             }
    #         ]
    #     },
    #     proxies = {
    #         # 'http': http_proxy,
    #         'https': https_proxy
    #     },
    #     verify = False
    # )

    # print(response.status_code)
    # print(response.content)


@main.command()
@argument('path', type = str)
def stats(path: str):
    Tables.from_dir(path).non_trivial.stats.print()

    # n_tables = 0

    # n_cells_ = []
    # n_rows_ = []
    # n_cols_ = []
    # n_chars_ = []

    # total_length = 0

    # for file in os.listdir(path):
    #     with open(os.path.join(path, file), 'r') as file:
    #         n_tables += 1
    #         table = json.load(file)

    #         total_length += len(json.dumps(table, ensure_ascii = False, indent = 2))

    #         n_cells = 0
    #         n_rows = 0
    #         n_cols = 0

    #         for row in table['rows']:
    #             n_rows += 1

    #             n_cols_local = 0

    #             for cell in row:
    #                 if (cell_text := cell.get('text')) is not None:
    #                     n_cols_local += 1
    #                     # print(cell_text)
    #                     n_chars_.append(len(cell_text))

    #             n_cells += (n_cols_local := len([cell for cell in row if 'text' in cell]))  # if 'text' not in cell then it is a placeholder

    #             if n_cols_local > n_cols:
    #                 n_cols = n_cols_local

    #         n_rows_.append(n_rows)
    #         n_cols_.append(n_cols)
    #         n_cells_.append(n_cells)

    # def print_percentiles(label: str, data: list):
    #     percentiles = ' '.join(map(''.join, zip(('5%: ', '25%: ', '50%: ', '75%: ', '95%: '), map(lambda value: f'{value:.3f}', percentile(data, (5, 25, 50, 75, 95))))))
    #     print(f'{label}: {percentiles}')

    # print('Number of tables:', n_tables)
    # print('Total length:', total_length)

    # print_percentiles('Number of cells', n_cells_)
    # print_percentiles('Number of rows', n_rows_)
    # print_percentiles('Number of columns', n_cols_)
    # print_percentiles('Text length', n_chars_)


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
@option('--first-n', '-n', type = int, required = False)
def translate(source: str, destination: str, first_n: int):
    print('Collecting texts...')

    if not os.path.isdir(destination):
        os.makedirs(destination)

    texts = []
    tables = []

    source_files = os.listdir(source)

    if first_n is not None:
        source_files = source_files[:first_n]

    for source_file in source_files:
        with open(os.path.join(source, source_file), 'r') as file:
            table = json.load(file)

            for row in table['rows']:
                for cell in row:
                    if (text := cell.get('text')) is not None and len(text) > 0 and not is_number(text):
                        texts.append(text)
                        cell['_requires-translation'] = True
                    else:
                        cell['_requires-translation'] = False

            table['_filename'] = source_file

            tables.append(table)

    # print(len(texts))
    # print(tables[0])

    print('Translating...')

    translator = TableTranslator()

    translated_texts = translator.translate_row(texts)

    with open('assets/new-specs/translation-log.txt', 'w') as file:
        for text, translated_text in zip(texts, translated_texts):
            file.write(f'{text} 🔴 {translated_text}\n')

    offset = 0

    for table in tables:
        for row in table['rows']:
            for cell in row:
                if cell.pop('_requires-translation'):
                    cell['text'] = translated_texts[offset]
                    offset += 1

        filename = table.pop('_filename')

        with open(os.path.join(destination, filename), 'w') as file:
            json.dump(table, file, indent = 2, ensure_ascii = False)


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
