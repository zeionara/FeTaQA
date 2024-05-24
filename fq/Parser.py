import os
import re
from pathlib import Path
from enum import Enum

from tqdm import tqdm
from docx.api import Document
from bs4 import BeautifulSoup

from .util import normalize_spaces, is_bold, has_not_fewer_dots_than, drop_space_around_punctuation
from .util.soup import get_first_non_empty_element
from .Table import Table


PARAGRAPH_SEP_PLACEHOLDER = '__PARAGRAPH_SEP__'
PARAGRAPH_SEP = '\n\n'
TABLE_ID = re.compile('[A-ZА-Я0-9.Ё]+')
APPLICATION_ID = re.compile('[A-ZА-ЯЁ]+')
APPLICATION_TABLE_ID = re.compile('([A-ZА-ЯЁ]+).+')
NOT_APPLICATION_TABLE_ID = re.compile(r'\w+')


def join_paragraphs(paragraphs: list):
    if len(paragraphs) < 1:
        return None

    return normalize_spaces(PARAGRAPH_SEP_PLACEHOLDER.join(paragraphs)).replace(PARAGRAPH_SEP_PLACEHOLDER, PARAGRAPH_SEP)


def extract_id(id_, pattern, text: str):
    for match in pattern.findall(text):
        id_candidate = str(match)

        if id_ is None or len(id_candidate) >= len(id_):
            id_ = id_candidate

    return id_


class TableType(Enum):
    TABLE = 'table'
    APPLICATION = 'application'
    FORM = 'form'


class Parser:
    def __init__(self, context_window_size: int = 5, json_indent: int = 2):
        self.context_window_size = context_window_size
        self.json_indent = json_indent

    def get_context(self, paragraphs):
        window = self.context_window_size

        context = []

        title = []
        id_ = None
        table_type = None
        found_reference = False
        there_are_paragraphs_with_full_id = False

        for j, paragraph in enumerate(paragraphs):
            text = drop_space_around_punctuation(normalize_spaces(paragraph.text))

            previous_paragraphs = paragraph.findPreviousSiblings('w:p')
            next_paragraphs = paragraph.findNextSiblings('w:p')

            if len(text.strip()) > 0:
                normalized_text = text.lower().strip()

                if normalized_text.startswith('библиография'):
                    title.append(text)
                    id_ = text
                    table_type = TableType.TABLE
                elif id_ is None and normalized_text.startswith('таблица'):
                    title.append(text)

                    for match in TABLE_ID.findall(text):
                        id_candidate = str(match)

                        if id_ is None or len(id_candidate) >= len(id_) and has_not_fewer_dots_than(id_candidate, id_):
                            id_ = id_candidate

                            try:
                                int(id_)
                                break
                            except ValueError:
                                pass

                    there_are_paragraphs_with_full_id = any(id_ in paragraph.text for paragraph in previous_paragraphs)
                    application_table_id_match = APPLICATION_TABLE_ID.fullmatch(id_)

                    if application_table_id_match is not None and text.endswith(id_):
                        last_paragraph = get_first_non_empty_element(previous_paragraphs)
                        table_type = TableType.APPLICATION

                        if is_bold(paragraph) and is_bold(last_paragraph) or not is_bold(paragraph) and not is_bold(last_paragraph):
                            title.append(last_paragraph._element.text)
                    else:
                        table_type = TableType.TABLE
                elif id_ is None and normalized_text.startswith('форма'):
                    title.append(text)
                    title.append(get_first_non_empty_element(next_paragraphs).text)

                    id_ = extract_id(id_, TABLE_ID, text)

                    table_type = TableType.FORM
                elif id_ is None and normalized_text.startswith('приложение'):
                    title.append(text)
                    title.append(get_first_non_empty_element(next_paragraphs).text)

                    id_ = extract_id(id_, APPLICATION_ID, text)

                    table_type = TableType.APPLICATION
                else:
                    if id_ is None or NOT_APPLICATION_TABLE_ID.fullmatch(id_):
                        application_table_id_match = None
                    else:
                        application_table_id_match = APPLICATION_TABLE_ID.fullmatch(id_)

                    if not normalized_text.startswith('табл') and (
                        id_ is not None and
                        (
                            table_type == TableType.TABLE and (
                                'табл' in normalized_text and there_are_paragraphs_with_full_id or
                                'приложен' in normalized_text and not there_are_paragraphs_with_full_id
                            ) or
                            (
                                table_type == TableType.APPLICATION or
                                application_table_id_match is not None
                            ) and (
                                not there_are_paragraphs_with_full_id and 'приложен' in normalized_text or
                                there_are_paragraphs_with_full_id and 'табл' in normalized_text
                            ) or
                            table_type == TableType.FORM and ' форм' in normalized_text
                        ) and
                        (
                            id_ in text or
                            table_type == TableType.FORM or
                            (
                                application_table_id_match is not None and
                                (
                                    not there_are_paragraphs_with_full_id and
                                    re.search(r'\s' + application_table_id_match.group(1) + r'[^\w\s]', text) is not None
                                ) and
                                not text.endswith(application_table_id_match.group(1))
                            )
                        )
                    ):
                        found_reference = True

                    if found_reference:
                        context.append(text)
                        window -= 1

                        if window < 1:
                            break

        # print('Context:')
        # print(len(context))
        # print('Title:')
        # print(title)

        return join_paragraphs(context[::-1]), join_paragraphs(title), id_

    def parse_file(self, source: str, get_destination: callable = None):
        document = Document(source)

        soup = BeautifulSoup(document._element.xml, 'lxml')

        if get_destination is None:
            stem = Path(source).stem

            def get_destination(i: int):
                return f'{stem}.{i:04d}'.replace('-', '_') + '.json'

        for i, table in list(enumerate(soup.find_all('w:tbl')))[1:]:
            yield Table.from_soup(
                table, get_destination(i), *self.get_context(
                    table.findPreviousSiblings('w:p')
                )
            )

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
