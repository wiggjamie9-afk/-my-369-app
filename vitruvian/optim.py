"""Muon optimizer (momentum + orthogonalised updates), the approach Moonshot
published for training Kimi K2. Written from the public description.

Matrix weights (2-D, plus 3-D stacks of expert matrices) use Muon. Embeddings,
norms and other vectors use AdamW, as the published recipe does.
"""
import torch


def orthogonalize(g, steps=5):
    """Approximately replace G with U V^T (from its SVD) using a Newton-Schulz
    iteration. Works on a single matrix or a batch of matrices."""
    a, b, c = 3.4445, -4.7750, 2.0315
    x = g.float()
    tall = x.size(-2) > x.size(-1)
    if tall:
        x = x.mT
    x = x / (x.norm(dim=(-2, -1), keepdim=True) + 1e-7)
    for _ in range(steps):
        s = x @ x.mT
        x = a * x + (b * s + c * s @ s) @ x
    return (x.mT if tall else x).to(g.dtype)


class Muon(torch.optim.Optimizer):
    def __init__(self, params, lr=2e-3, momentum=0.95, weight_decay=0.1):
        super().__init__(params, dict(lr=lr, momentum=momentum, weight_decay=weight_decay))

    @torch.no_grad()
    def step(self):
        for group in self.param_groups:
            for p in group["params"]:
                if p.grad is None:
                    continue
                buf = self.state[p].setdefault("momentum", torch.zeros_like(p))
                buf.mul_(group["momentum"]).add_(p.grad)
                update = orthogonalize(p.grad + group["momentum"] * buf)
                # match AdamW's update size so the same lr works for both
                scale = 0.2 * max(p.size(-2), p.size(-1)) ** 0.5
                p.mul_(1 - group["lr"] * group["weight_decay"])
                p.add_(update, alpha=-group["lr"] * scale)


def build_optimizers(model, lr=2e-3):
    matrices = [p for n, p in model.named_parameters() if p.ndim >= 2 and "embed" not in n]
    others = [p for n, p in model.named_parameters() if p.ndim < 2 or "embed" in n]
    return [
        Muon(matrices, lr=lr),
        torch.optim.AdamW(others, lr=lr, betas=(0.9, 0.95), weight_decay=0.0),
    ]
