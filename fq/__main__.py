from click import argument, group, option
from camelot import read_pdf
from numpy import percentile
from transformers import pipeline
from tqdm import tqdm


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
