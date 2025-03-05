import os
from os import environ as env
import json
import shutil
# from time import sleep

import matplotlib.pyplot as plt
from click import argument, group, option
from numpy import percentile, random as np_random, mean, std
# from tqdm import tqdm
from pathlib import Path
# from docx.api import Document
from requests import post
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from pandas import read_csv
# from camelot import read_pdf

from .util import unpack, is_number  # , normalize_spaces
# from .Cell import Cell
from .Tables import Tables
# from .TableTranslator import TableTranslator
from .Parser import Parser, DEFAULT_EMBEDDING_MODEL


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
@option('--n-clusters', '-n', type = int, default = 2)
@option('--seed', '-s', type = int, default = 17)
def clusterize(path: str, n_clusters: int, seed: int):
    pca = PCA(n_components = 2)
    df = read_csv(path, sep = '\t')

    df_compressed = pca.fit_transform(df)
    df_compressed_jitter = df_compressed + np_random.normal(loc = 0, scale = 0.01, size = df_compressed.shape)

    kmeans = KMeans(n_clusters = n_clusters, random_state = seed)
    cluster_labels = kmeans.fit_predict(df)

    # print(cluster_labels)

    n_files_per_cluster = [0 for _ in range(n_clusters)]
    jsons_path = path.split('.')[0]
    clusters_path = jsons_path + '_clusters'
    labels_path = jsons_path + '.txt'

    labels = []

    with open(labels_path, 'r') as file:
        for line in file.readlines():
            labels.append(line[:-1])

    if os.path.isdir(clusters_path):
        shutil.rmtree(clusters_path)

    for i in range(0, n_clusters):
        os.makedirs(os.path.join(clusters_path, f'{i:02d}'))

    for file, cluster in zip(labels, cluster_labels):
        n_files_per_cluster[cluster] += 1
        shutil.copy(os.path.join(jsons_path, file), os.path.join(clusters_path, f'{cluster:02d}', file))

    for cluster, count in sorted([(i, count) for i, count in enumerate(n_files_per_cluster)], key = lambda item: item[1], reverse = True):
        print(f'{cluster:02d}: {count:03d}')

    print(f'Mean n tables per cluster: {mean(n_files_per_cluster):.3f}, Std: {std(n_files_per_cluster):.3f}')

    plt.figure(figsize=(8, 6))
    plt.scatter(df_compressed_jitter[:, 0], df_compressed_jitter[:, 1], s = 10, c = cluster_labels, cmap = 'tab20')
    plt.title('Table features PCAed to 2 dimensions')
    plt.xlabel('Principal Component 1')
    plt.ylabel('Principal Component 2')
    plt.xscale('log')
    plt.yscale('log')
    plt.grid(True)
    plt.show()


@main.command()
@argument('path', type = str)
@option('--save', '-s', is_flag = True)
def stats(path: str, save: bool):
    if save:
        (tables := Tables.from_dir(path).non_trivial).stats.as_df.to_csv(f'{path}.tsv', index = False, sep = '\t')

        with open(f'{path}.txt', 'w') as file:
            for label in tables.labels:
                file.write(f'{label}\n')
    else:
        Tables.from_dir(path).non_trivial.stats.print()


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
    from .TableTranslator import TableTranslator

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

            if (context := table.get('context')) is not None:
                texts.append(context)

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

        if (context := table.get('context')) is not None:
            table['context'] = translated_texts[offset]
            offset += 1

        with open(os.path.join(destination, filename), 'w') as file:
            json.dump(table, file, indent = 2, ensure_ascii = False)


@main.command()
@argument('source', type = str)
def view(source: str):
    parser = Parser()

    for table in parser.parse_file(source):
        print('=' * 100)
        print(f'🔵 Title: {table.title}')
        print(f'🔵 >>>> {table.content}')
        print(f'🔵 ++++ {table.context}')


@main.command()
@argument('source', type = str, default = 'assets/specs')
@argument('destination', type = str, default = 'assets/records')
@option('--cpu', '-c', is_flag = True)
@option('--embedding-model', '-e', type = str, default = DEFAULT_EMBEDDING_MODEL)
def parse(source: str, destination: str, cpu: bool, embedding_model: str):
    Parser().parse(source, destination, cpu, embedding_model)


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
