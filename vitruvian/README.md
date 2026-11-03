# Vitruvian-369 — your own language model

An original model written from scratch. It copies no weights or code from
any other model. Instead it combines the best architecture ideas the big
labs have **published openly** in their papers.

## The best bits, and where each idea comes from

| Part | What it does | Idea from |
|---|---|---|
| Decoder-only transformer, RMSNorm pre-norm | The core design behind all modern chat models | Llama, Qwen |
| Rotary position embeddings (RoPE) | Tells the model where each token sits in the text | RoFormer; used almost everywhere |
| Grouped-query attention | Several query heads share one key/value head, so less memory and faster generation | Llama 2+, Qwen |
| QK-norm | Normalises queries and keys so attention can't blow up during training | Qwen 3 |
| SwiGLU feed-forward | A better "thinking" layer than the old ReLU MLP | PaLM, Llama |
| Mixture-of-Experts + shared expert | Many small expert networks; each token uses only 2, so you get a big model's capacity for a small model's compute | DeepSeek-V3, Kimi K2 |
| Sigmoid routing, aux-loss-free balancing | Keeps all experts busy without an extra loss term fighting the main one | DeepSeek-V3, Kimi K2 |
| First layer dense, the rest MoE | Lower layers learn general features; experts specialise higher up | DeepSeek-V3, Kimi K2 |
| Muon optimizer | Orthogonalised updates that train faster than AdamW | Kimi K2 (Moonshot) |
| Byte-level tokens, tied embeddings | No tokenizer to download; works for any language | Small-model practice |

## Files

- `model.py`: the architecture
- `optim.py`: the Muon optimizer
- `train.py`: training, checkpointing and text generation

## Run it

```bash
pip install torch
python vitruvian/train.py                       # demo: trains on Python's own source code
python vitruvian/train.py --data my.txt --steps 3000   # train on your own text
python vitruvian/train.py --sample "Once upon a time"   # write with the saved model
```

## First result

The default config has 3.7M parameters: 4 layers, 8 experts with top-2 routing,
and 1 shared expert. It ran for 1,500 steps on a 4-core CPU with no GPU and
took about 9 minutes. Validation loss fell from 5.53 to 0.98. It has learned
the shape of Python but doesn't yet make sense:

```python
def __iter__(self, other):
        return self.__str__(self, other)

class _Private(self, other):
    """Close that do class own bytes.  Everything empty of sys.
```

## Making it smarter

Quality comes from scale: parameters × training data × compute. The code
stays the same; you change the numbers in `Config`:

| Size | Config change | Hardware | Expect |
|---|---|---|---|
| ~4M (now) | default | any CPU | text that looks right |
| ~100M | `dim=768, layers=12, experts=16` | 1 consumer GPU, a day | grammatical English |
| ~1B+ | bigger again, plus a real tokenizer | rented multi-GPU | basic Q&A, once fine-tuned on chat data |

Matching Kimi or Claude takes thousands of GPUs and trillions of tokens. That
isn't a code problem. A small model trained well on **your own** niche data
can still be useful, and it's entirely yours.
