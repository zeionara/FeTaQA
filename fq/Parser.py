import os
import re
from pathlib import Path
from enum import Enum

from tqdm import tqdm
from docx.api import Document

from .util import normalize_spaces, is_bold, has_not_fewer_dots_than
from .Table import Table


PARAGRAPH_SEP_PLACEHOLDER = '__PARAGRAPH_SEP__'
PARAGRAPH_SEP = '\n\n'
TABLE_ID = re.compile('[A-ZА-Я0-9.Ё]+')
APPLICATION_ID = re.compile('[A-ZА-ЯЁ]+')
APPLICATION_TABLE_ID = re.compile('([A-ZА-ЯЁ]+).+')
NOT_APPLICATION_TABLE_ID = re.compile(r'\w+')

DEBUG = False


class TableType(Enum):
    TABLE = 'table'
    APPLICATION = 'application'
    FORM = 'form'


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

        def get_last_non_empty_paragraph(paragraphs: list):
            for paragraph in paragraphs[::-1]:
                if is_not_empty(paragraph._element.text):
                    return paragraph

        def join_paragraphs(paragraphs: list):
            if len(paragraphs) < 1:
                return None

            return normalize_spaces(PARAGRAPH_SEP_PLACEHOLDER.join(paragraphs)).replace(PARAGRAPH_SEP_PLACEHOLDER, PARAGRAPH_SEP)

        if first_paragraph_element_after_the_table is None:  # Then probably the table is the last element of the document
            last_non_empty_paragraph = get_last_non_empty_paragraph(paragraphs)

        i = 0

        context = []
        offset = 0 if first_paragraph_element_after_the_table is None else 1

        title = []
        id_ = None
        table_type = None
        found_reference = False
        there_are_paragraphs_with_full_id = False

        for paragraph in paragraphs:
            if (
                first_paragraph_element_after_the_table is None and paragraph._element.text == last_non_empty_paragraph._element.text or
                first_paragraph_element_after_the_table is not None and paragraph._element.text == first_paragraph_element_after_the_table.text
            ):
                while window > 0 and i >= offset:
                    text = (paragraph := paragraphs[i - offset])._element.text

                    if text is not None and len(text.strip()) > 0:
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

                            there_are_paragraphs_with_full_id = any(id_ in paragraph._element.text for paragraph in paragraphs[:i - offset])
                            application_table_id_match = APPLICATION_TABLE_ID.fullmatch(id_)

                            if application_table_id_match is not None and text.endswith(id_):
                                last_paragraph = get_last_non_empty_paragraph(paragraphs[:i - offset])
                                table_type = TableType.APPLICATION

                                if is_bold(paragraph) and is_bold(last_paragraph) or not is_bold(paragraph) and not is_bold(last_paragraph):
                                    title.append(last_paragraph._element.text)
                            else:
                                table_type = TableType.TABLE
                        elif id_ is None and normalized_text.startswith('форма'):
                            title.append(text)
                            title.append(get_last_non_empty_paragraph(paragraphs[i - offset + 1:][::-1])._element.text)

                            for match in TABLE_ID.findall(text):
                                id_candidate = str(match)

                                if id_ is None or len(id_candidate) >= len(id_):
                                    id_ = id_candidate

                            table_type = TableType.FORM
                        elif id_ is None and normalized_text.startswith('приложение'):
                            title.append(text)
                            title.append(get_last_non_empty_paragraph(paragraphs[i - offset + 1:][::-1])._element.text)

                            for match in APPLICATION_ID.findall(text):
                                id_candidate = str(match)

                                if id_ is None or len(id_candidate) >= len(id_):
                                    id_ = id_candidate

                            table_type = TableType.APPLICATION
                        else:
                            # print('>>', text)

                            if id_ is None or NOT_APPLICATION_TABLE_ID.fullmatch(id_):
                                application_table_id_match = None
                            else:
                                application_table_id_match = APPLICATION_TABLE_ID.fullmatch(id_)

                            # print(application_table_id_match)

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
                                    ) and (not there_are_paragraphs_with_full_id and 'приложен' in normalized_text or there_are_paragraphs_with_full_id and 'табл' in normalized_text) or
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
                                        # application_table_id_match.group(1) in text and
                                        not text.endswith(application_table_id_match.group(1))
                                    )
                                )
                            ):
                                found_reference = True

                            # if id_ == 'В.1' and 'таблице В.1':
                            #     print(found_reference, text)
                            #     print(there_are_paragraphs_with_full_id)
                            #     print(
                            #         table_type,
                            #         application_table_id_match,
                            #         there_are_paragraphs_with_full_id,
                            #         'табл' in normalized_text,
                            #         (
                            #             table_type == TableType.TABLE and (
                            #                 'табл' in normalized_text and there_are_paragraphs_with_full_id or
                            #                 'приложен' in normalized_text and not there_are_paragraphs_with_full_id
                            #             ),
                            #             (
                            #                 (
                            #                     table_type == TableType.APPLICATION or
                            #                     application_table_id_match is not None
                            #                 ),
                            #                 (not there_are_paragraphs_with_full_id and 'приложен' in normalized_text or there_are_paragraphs_with_full_id and 'табл' in normalized_text)
                            #             ),
                            #             table_type == TableType.FORM and ' форм' in normalized_text
                            #         )
                            #     )
                            #     dd

                            # if id_ == 'Д.1' and 'вестибюли, операционные, кассовые залы, залы ожидания и др.' in text:
                            #     print(found_reference, table_type)
                            #     print(text)
                            #     print(there_are_paragraphs_with_full_id)
                            #     dd

                            # if id_ == 'Г.1' and 'согласно таблице Г.2' in text:
                            #     print(found_reference, there_are_paragraphs_with_full_id)
                            #     dd

                            # print(found_reference)
                            # print(
                            #     table_type == TableType.APPLICATION,
                            #     application_table_id_match is not None,
                            #     'приложен' in normalized_text
                            # )
                            # print(
                            #     id_ is not None,
                            #     (
                            #         table_type == TableType.TABLE and 'табл' in normalized_text or
                            #         (
                            #             table_type == TableType.APPLICATION or
                            #             application_table_id_match is not None
                            #         ) and ('приложен' in normalized_text or 'табл' in normalized_text) or
                            #         table_type == TableType.FORM and ' форм' in normalized_text
                            #     ),
                            #     (
                            #         id_ in text or
                            #         table_type == TableType.FORM or
                            #         (
                            #             application_table_id_match is not None and
                            #             re.search(r'\s' + application_table_id_match.group(1) + r'[^\w]', text) is not None and
                            #             # application_table_id_match.group(1) in text and
                            #             not text.endswith(application_table_id_match.group(1))
                            #         )
                            #     )
                            # )

                            # if 'в таблице Б.1.' in text:
                            #     dd

                            if found_reference:
                                context.append(text)
                                window -= 1

                    offset += 1

            i += 1

        return join_paragraphs(context[::-1]), join_paragraphs(title), id_

    def parse_file(self, source: str, get_destination: callable = None):
        document = Document(source)

        if get_destination is None:
            stem = Path(source).stem

            def get_destination(i: int):
                return f'{stem}.{i:04d}'.replace('-', '_') + '.json'

        for i, table in enumerate(document.tables):
            if DEBUG:
                context, title, id_ = self.get_context(document, table)

                yield Table.from_docx(
                    table,
                    label = (destination := get_destination(i)),
                    context = context,
                    title = title,
                    id_ = id_
                )
            else:
                try:
                    context, title, id_ = self.get_context(document, table)

                    yield Table.from_docx(
                        table,
                        label = (destination := get_destination(i)),
                        context = context,
                        title = title,
                        id_ = id_
                    )
                except IndexError:
                    print(f"Can't parse table {destination} due to index error")

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
