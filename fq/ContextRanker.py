import re

from transformers import AutoTokenizer, AutoModel
from torch import Tensor
import torch.nn.functional as F
import matplotlib.pyplot as plt

from .Table import Table
from .Paragraph import Paragraph


TABLE_ID_REGEX = re.compile(r'([0-9]+(\.[0-9]+)?)(\s+)?[.;]?(\s+)?$')
DEFAULT_MODEL = 'intfloat/multilingual-e5-large-instruct'


def to_cuda(data: dict):
    data_on_cuda = {}

    for key, value in data.items():
        data_on_cuda[key] = value.to('cuda')

    return data_on_cuda


def average_pool(  # compute average token embeddings for each input document
    last_hidden_states: Tensor,
    attention_mask: Tensor
) -> Tensor:
    last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]


class ContextRanker:
    def __init__(self, model: str = DEFAULT_MODEL, cuda: bool = True):
        self.tokenizer = AutoTokenizer.from_pretrained(model)
        self.model = AutoModel.from_pretrained(model)
        self.cuda = cuda

        if cuda:
            self.model.to('cuda')

    def rank(self, table: Table, paragraphs: list[Paragraph], infer_table_id: bool = False):
        input_texts = [
            f'Instruct: Given serialized table, retrieve relevant paragraphs which make up the table context\nQuery: {table.as_text}',
            *[paragraph.text for paragraph in paragraphs]
        ]
        
        if infer_table_id:
            match_counters = {}
            match_paragraphs = {}

            max_counter_match = None
            max_counter = None

            for paragraph in paragraphs:
                for match_ in TABLE_ID_REGEX.findall(paragraph.text):
                    group = match_[0]

                    if group in match_counters:
                        match_counter = match_counters[group] + 1
                        match_counters[group] = match_counter
                        match_paragraphs[group].append(paragraph)
                    else:
                        match_counters[group] = match_counter = 1
                        match_paragraphs[group] = [paragraph]

                    if max_counter is None or match_counter > max_counter:
                        max_counter = match_counter
                        max_counter_match = group

            max_counter_paragraphs = match_paragraphs[max_counter_match]

        # print(table.as_text)
        # print([paragraph.text for paragraph in paragraphs])

        batch_dict = self.tokenizer(input_texts, max_length = 512, padding = True, truncation = True, return_tensors = 'pt')

        if self.cuda:
            batch_dict = to_cuda(batch_dict)

        outputs = self.model(**batch_dict)

        text_embeddings = average_pool(outputs.last_hidden_state, batch_dict['attention_mask'])
        text_embeddings = F.normalize(text_embeddings, p = 2, dim = 1)

        scores = (text_embeddings[:1] @ text_embeddings[1:].T).tolist()[0]

        plt.plot(sorted(scores, reverse = True))
        plt.savefig('assets/scores.png')

        scores_and_paragraphs = list(zip(scores, paragraphs))

        if infer_table_id:
            for i, item in enumerate(scores_and_paragraphs):
                if item[1] in max_counter_paragraphs:
                    scores_and_paragraphs[i] = (1.0, item[1])

        i = 1

        for score, paragraph in sorted(scores_and_paragraphs, key = lambda item: item[0], reverse = True):
            print(i, f'{score:.3f}', paragraph.text)
            i += 1
