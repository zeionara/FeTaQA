from transformers import pipeline, AutoTokenizer
from tqdm import tqdm

from .util import unescape_translation


MAX_LENGTH = 512


class TableTranslator:
    def __init__(self, model: str = 'Helsinki-NLP/opus-mt-ru-en'):
        self.pipeline = pipeline('translation', model = model, framework = 'pt', device = 'cuda', max_length = MAX_LENGTH)
        self.tokenizer = AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-ru-en")

    def count(self, text: str):
        return len(self.tokenizer(text)['input_ids'])

    def _split(self, text: str):
        text_components = text.split(' ')
        middle_index = len(text_components) // 2

        chunks = []

        lhs = ' '.join(text_components[:middle_index])
        rhs = ' '.join(text_components[middle_index:])

        def push(half: str):
            if self.count(half) > MAX_LENGTH:
                for chunk in self._split(half):
                    chunks.append(chunk)
            else:
                chunks.append(half)

        push(lhs)
        push(rhs)

        return chunks

    def translate_row(self, row: list[str]):
        merge_flags = []
        row_chunks = []

        for item in row:
            if self.count(item) > MAX_LENGTH:
                chunks = self._split(item)

                for chunk in chunks:
                    row_chunks.append(chunk)

                merge_flags.append(False)
                merge_flags.extend([True for _ in range(len(chunks) - 1)])
            else:
                row_chunks.append(item)
                merge_flags.append(False)

        translated_texts = [cell['translation_text'] for cell in self.pipeline(row_chunks)]
        final_texts = []

        last_text = None

        for text, should_merge_with_last in zip(translated_texts, merge_flags):
            if last_text is not None:
                if should_merge_with_last:
                    last_text = ' '.join((last_text, text))
                    # print(last_text)
                else:
                    final_texts.append(unescape_translation(last_text))
                    last_text = text
            else:
                last_text = text

        final_texts.append(last_text)

        return final_texts

    def translate(self, table: list[list[str]]):
        translated_table = []

        for row in tqdm(table, desc = 'Translating table'):
            translated_table.append(self.translate_row(row))

        return translated_table
