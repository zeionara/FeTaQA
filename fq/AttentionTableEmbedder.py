from transformers import AutoModel
from torch import reshape, cat
from torch.nn import Module, Linear
from torch.nn.functional import pad, softmax


class AttentionTableEmbedder(Module):

    def __init__(self, base_model: str, max_length: int, cuda: bool = True):
        super().__init__()

        self.base_model = base_model
        self._base_model = _base_model = AutoModel.from_pretrained(base_model)

        self.hidden_size = hidden_size = _base_model.config.hidden_size
        self.max_length = max_length

        self.row_wise_attention = row_wise_attention = Linear(max_length * hidden_size, 1)
        self.column_wise_attention = column_wise_attention = Linear(max_length * hidden_size, 1)

        self.table_wise_attention = table_wise_attention = Linear(max_length * hidden_size, 1)

        if cuda:
            _base_model.to('cuda')

            row_wise_attention.to('cuda')
            column_wise_attention.to('cuda')
            table_wise_attention.to('cuda')

    def forward(self, *args, n_levels: int, **kwargs):
        # embedding

        embeddings = self._base_model(*args, **kwargs).last_hidden_state

        new_shape = (n_levels, embeddings.shape[0] // n_levels) + embeddings.shape[1:]
        embeddings = reshape(embeddings, new_shape)

        # row-wise attention

        x = embeddings
        x = pad(embeddings, (0, 0, self.max_length - embeddings.shape[2], 0))
        a, b, c, d = x.shape

        # Flatten spatial dimensions
        x_flat = x.view(a, b, -1)  # [a, b, c*d]

        # Compute attention scores for each element along dimension b
        attn_scores = self.row_wise_attention(x_flat)  # [a, b, 1]

        # Normalize the attention scores along dimension b
        attn_weights = softmax(attn_scores, dim=1)  # [a, b, 1]

        # Expand weights to match flattened input shape
        attn_weights = attn_weights.expand(-1, -1, c * d)  # [a, b, c*d]

        # Apply attention weights and sum along dimension b
        x_weighted = (x_flat * attn_weights).sum(dim=1)  # [a, c*d]

        # Reshape back to [a, c, d]
        x_weighted = x_weighted.view(a, c, d)

        row_embeddings = x_weighted  # [:, :embeddings.shape[2], :]

        # column-wise attention

        # Flatten the last two dimensions
        # x_flat = x.view(a, b, -1)  # [a, b, c*d]

        # Transpose to make the first dimension the batch dimension
        x_flat = x_flat.permute(1, 0, 2)  # [b, a, c*d]

        # Apply linear layer to compute attention scores
        attn_scores = self.column_wise_attention(x_flat)  # [b, a, c*d]

        # Normalize the scores with softmax along the sequence dimension (a)
        attn_weights = softmax(attn_scores, dim=1)  # [b, a, c*d]

        # Weighted sum
        x_weighted = (x_flat * attn_weights).sum(dim=1)  # [b, c*d]
        x_weighted = x_weighted.view(b, c, d)

        column_embeddings = x_weighted  # [:, :embeddings.shape[2], :]

        # global attention

        x = cat((row_embeddings, column_embeddings), dim = 0)

        x_flat = x.view(a + b, -1)  # [a + b, c*d]

        # Apply linear layer to compute attention scores
        attn_scores = self.table_wise_attention(x_flat)  # [b, a, c*d]

        # Normalize the scores with softmax along the sequence dimension (a)
        attn_weights = softmax(attn_scores, dim=0)  # [b, a, c*d]

        # Weighted sum
        x_weighted = (x_flat * attn_weights).sum(dim=0)  # [c*d]
        x_weighted = x_weighted.view(c, d)

        table_embeddings = x_weighted  # [:, :embeddings.shape[2], :]

        # Reshape back to [b, c, d]
        # x_weighted = x_weighted.view(b, c, d)

        # x = embeddings
        # x = pad(embeddings, (0, 0, self.level_size - embeddings.shape[2], 0))

        # # Flatten spatial dimensions
        # x_flat = x.view(a, b, -1)  # [a, b, c*d]

        # # Compute attention scores for each element along the first dimension [a]
        # attn_scores = self.row_wise_attention(x_flat)  # [a, b, 1] - one score per cell

        # # Apply softmax along the first dimension (a)
        # attn_weights = F.softmax(attn_scores, dim=0)  # [a, b, 1]

        # # Expand attention weights to match input shape
        # attn_weights = attn_weights.expand(-1, -1, c * d)  # [a, b, c*d]

        # # Apply weights and sum along the first dimension
        # x_weighted = (x_flat * attn_weights).sum(dim=0)  # [b, c*d]

        # # Reshape back to [b, c, d]
        # x_weighted = x_weighted.view(b, c, d)

        # a, b, c, d = x.shape
        # 
        # # Flatten the last two dimensions
        # x_flat = x.view(a, b, -1)  # [a, b, c*d]

        # # Transpose to make the first dimension the batch dimension
        # x_flat = x_flat.permute(1, 0, 2)  # [b, a, c*d]

        # # Apply linear layer to compute attention scores
        # attn_scores = self.attention(x_flat)  # [b, a, c*d]

        # # Normalize the scores with softmax along the sequence dimension (a)
        # attn_weights = F.softmax(attn_scores, dim=1)  # [b, a, c*d]

        # # Weighted sum
        # x_weighted = (x_flat * attn_weights).sum(dim=1)  # [b, c*d]

        # # Reshape back to [b, c, d]
        # x_weighted = x_weighted.view(b, c, d)

        return table_embeddings
