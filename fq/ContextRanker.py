from transformers import AutoTokenizer, AutoModel

from .Table import Table
from .Paragraph import Paragraph


def to_cuda(data: dict):
    data_on_cuda = {}

    for key, value in data.items():
        data_on_cuda[key] = value.to('cuda')

    return data_on_cuda


class ContextRanker:
    def __init__(self, model: str = 'intfloat/multilingual-e5-large-instruct', cuda: bool = True):
        self.tokenizer = AutoTokenizer.from_pretrained(model)
        self.model = AutoModel.from_pretrained(model)
        self.cuda = cuda

        if cuda:
            self.model.to('cuda')

    def rank(self, table: Table, paragraphs: list[Paragraph]):
        input_texts = [
            f'Instruct: Given serialized table, retrieve relevant paragraphs which make up the table context\nQuery: {table.as_text}',
            *[paragraph.text for paragraph in paragraphs]
        ]

        # print(table.as_text)
        # print([paragraph.text for paragraph in paragraphs])

        batch_dict = self.tokenizer(input_texts, max_length = 512, padding = True, truncation = True, return_tensors = 'pt')

        if self.cuda:
            batch_dict = to_cuda(batch_dict)

        outputs = self.model(**batch_dict)

        print(outputs)
