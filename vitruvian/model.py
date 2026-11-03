"""Vitruvian-369: an original small language model.

Written from scratch. No weights or code are taken from any other model; it
combines architecture ideas that labs have published openly in their papers:

  * Decoder-only transformer, pre-norm with RMSNorm       (Llama / Qwen family)
  * Rotary position embeddings (RoPE)                     (RoFormer, used widely)
  * Grouped-query attention (fewer K/V heads)             (Llama 2+, Qwen)
  * QK-norm: RMSNorm on queries and keys per head         (Qwen 3) - keeps attention stable
  * SwiGLU feed-forward                                   (PaLM / Llama)
  * Mixture-of-Experts with a shared expert,
    sigmoid routing and aux-loss-free load balancing      (DeepSeek-V3, Kimi K2)
  * First layer(s) dense, the rest MoE                    (DeepSeek-V3, Kimi K2)
  * Tied input/output embeddings                          (small-model practice)

The optimizer (Muon, as used for Kimi K2) lives in optim.py.
"""
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class Config:
    vocab_size: int = 256          # byte-level: every UTF-8 byte is a token
    context: int = 256
    dim: int = 192
    layers: int = 4
    heads: int = 6
    kv_heads: int = 2              # grouped-query attention: 3 query heads share each K/V head
    dense_layers: int = 1          # the first N layers use a plain FFN, the rest are MoE
    ffn_hidden: int = 512          # hidden size of the dense FFN
    experts: int = 8               # routed experts per MoE layer
    experts_per_token: int = 2     # top-k
    shared_experts: int = 1        # always-on experts
    expert_hidden: int = 192
    rope_theta: float = 10000.0
    balance_rate: float = 1e-3     # speed of the aux-loss-free bias update


class RMSNorm(nn.Module):
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x):
        return self.weight * x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)


def rope_tables(head_dim, length, theta):
    freqs = 1.0 / theta ** (torch.arange(0, head_dim, 2).float() / head_dim)
    angles = torch.outer(torch.arange(length).float(), freqs)
    return angles.cos(), angles.sin()


def apply_rope(x, cos, sin):
    # x: (batch, heads, time, head_dim); rotate pairs of channels
    x1, x2 = x[..., 0::2], x[..., 1::2]
    out = torch.stack((x1 * cos - x2 * sin, x1 * sin + x2 * cos), dim=-1)
    return out.flatten(-2)


class Attention(nn.Module):
    def __init__(self, cfg: Config):
        super().__init__()
        self.heads, self.kv_heads = cfg.heads, cfg.kv_heads
        self.head_dim = cfg.dim // cfg.heads
        self.q = nn.Linear(cfg.dim, cfg.heads * self.head_dim, bias=False)
        self.kv = nn.Linear(cfg.dim, 2 * cfg.kv_heads * self.head_dim, bias=False)
        self.out = nn.Linear(cfg.heads * self.head_dim, cfg.dim, bias=False)
        self.q_norm = RMSNorm(self.head_dim)
        self.k_norm = RMSNorm(self.head_dim)

    def forward(self, x, cos, sin):
        b, t, _ = x.shape
        q = self.q(x).view(b, t, self.heads, self.head_dim).transpose(1, 2)
        k, v = self.kv(x).view(b, t, 2, self.kv_heads, self.head_dim).unbind(2)
        k, v = k.transpose(1, 2), v.transpose(1, 2)
        q, k = self.q_norm(q), self.k_norm(k)
        q, k = apply_rope(q, cos, sin), apply_rope(k, cos, sin)
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True, enable_gqa=True)
        return self.out(y.transpose(1, 2).reshape(b, t, -1))


class SwiGLU(nn.Module):
    def __init__(self, dim, hidden):
        super().__init__()
        self.gate = nn.Linear(dim, hidden, bias=False)
        self.up = nn.Linear(dim, hidden, bias=False)
        self.down = nn.Linear(hidden, dim, bias=False)

    def forward(self, x):
        return self.down(F.silu(self.gate(x)) * self.up(x))


class MoE(nn.Module):
    """Routed experts + shared expert(s).

    Routing uses sigmoid scores. A per-expert bias is added only when choosing
    the top-k experts (not to the mixing weights). After each training step the
    bias is nudged up for under-used experts and down for over-used ones, which
    balances load without an auxiliary loss term.
    """

    def __init__(self, cfg: Config):
        super().__init__()
        self.k = cfg.experts_per_token
        self.n = cfg.experts
        self.rate = cfg.balance_rate
        self.router = nn.Linear(cfg.dim, cfg.experts, bias=False)
        self.register_buffer("route_bias", torch.zeros(cfg.experts))
        self.register_buffer("load", torch.zeros(cfg.experts))
        e, d, h = cfg.experts, cfg.dim, cfg.expert_hidden
        self.w_gate = nn.Parameter(torch.randn(e, d, h) * d ** -0.5)
        self.w_up = nn.Parameter(torch.randn(e, d, h) * d ** -0.5)
        self.w_down = nn.Parameter(torch.randn(e, h, d) * h ** -0.5)
        self.shared = SwiGLU(d, h * cfg.shared_experts)

    def forward(self, x):
        shape = x.shape
        x = x.reshape(-1, shape[-1])
        scores = torch.sigmoid(self.router(x))
        _, idx = torch.topk(scores + self.route_bias, self.k, dim=-1)
        weights = scores.gather(-1, idx)
        weights = weights / weights.sum(-1, keepdim=True)

        out = torch.zeros_like(x)
        for e in range(self.n):
            token, slot = (idx == e).nonzero(as_tuple=True)
            if token.numel() == 0:
                continue
            h = F.silu(x[token] @ self.w_gate[e]) * (x[token] @ self.w_up[e])
            out.index_add_(0, token, (h @ self.w_down[e]) * weights[token, slot, None])

        if self.training:
            self.load += torch.bincount(idx.flatten(), minlength=self.n).float()
        return (out + self.shared(x)).reshape(shape)

    @torch.no_grad()
    def rebalance(self):
        if self.load.sum() > 0:
            self.route_bias += self.rate * torch.sign(self.load.mean() - self.load)
            self.load.zero_()


class Block(nn.Module):
    def __init__(self, cfg: Config, dense: bool):
        super().__init__()
        self.norm1 = RMSNorm(cfg.dim)
        self.attn = Attention(cfg)
        self.norm2 = RMSNorm(cfg.dim)
        self.ffn = SwiGLU(cfg.dim, cfg.ffn_hidden) if dense else MoE(cfg)

    def forward(self, x, cos, sin):
        x = x + self.attn(self.norm1(x), cos, sin)
        return x + self.ffn(self.norm2(x))


class Vitruvian(nn.Module):
    def __init__(self, cfg: Config):
        super().__init__()
        self.cfg = cfg
        self.embed = nn.Embedding(cfg.vocab_size, cfg.dim)
        self.blocks = nn.ModuleList(
            Block(cfg, dense=i < cfg.dense_layers) for i in range(cfg.layers)
        )
        self.norm = RMSNorm(cfg.dim)
        cos, sin = rope_tables(cfg.dim // cfg.heads, cfg.context, cfg.rope_theta)
        self.register_buffer("cos", cos, persistent=False)
        self.register_buffer("sin", sin, persistent=False)
        nn.init.normal_(self.embed.weight, std=0.02)

    def forward(self, tokens, targets=None):
        t = tokens.shape[1]
        x = self.embed(tokens)
        for block in self.blocks:
            x = block(x, self.cos[:t], self.sin[:t])
        logits = self.norm(x) @ self.embed.weight.T  # tied embeddings
        if targets is None:
            return logits
        return logits, F.cross_entropy(logits.flatten(0, 1), targets.flatten())

    def rebalance_experts(self):
        for m in self.modules():
            if isinstance(m, MoE):
                m.rebalance()

    @torch.no_grad()
    def generate(self, tokens, steps, temperature=0.8, top_k=40):
        for _ in range(steps):
            logits = self(tokens[:, -self.cfg.context:])[:, -1] / temperature
            cutoff = torch.topk(logits, top_k).values[:, -1, None]
            logits[logits < cutoff] = -float("inf")
            nxt = torch.multinomial(F.softmax(logits, -1), 1)
            tokens = torch.cat((tokens, nxt), dim=1)
        return tokens
