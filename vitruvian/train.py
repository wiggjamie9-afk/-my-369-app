"""Train Vitruvian-369 on any text file and print samples.

    python vitruvian/train.py --data my_text.txt --steps 2000
    python vitruvian/train.py --sample "Once upon a time"   # load checkpoint and write

With no --data it trains on the Python standard library's source code, which
is on every machine, so the demo runs anywhere with no download.
"""
import argparse
import math
import pathlib
import sys
import sysconfig
import time

import torch

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from model import Config, Vitruvian  # noqa: E402
from optim import build_optimizers  # noqa: E402

CKPT = pathlib.Path(__file__).parent / "vitruvian.pt"


def load_corpus(path):
    if path:
        return pathlib.Path(path).read_bytes()
    lib = pathlib.Path(sysconfig.get_paths()["stdlib"])
    files = sorted(lib.glob("*.py"))[:200]
    return b"\n".join(f.read_bytes() for f in files)


def encode(text):
    return torch.tensor(list(text.encode("utf-8")), dtype=torch.long)


def decode(tokens):
    return bytes(tokens.tolist()).decode("utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data")
    ap.add_argument("--steps", type=int, default=600)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--sample", help="skip training; continue this prompt")
    args = ap.parse_args()
    torch.manual_seed(369)

    if args.sample is not None:
        saved = torch.load(CKPT, weights_only=False)
        model = Vitruvian(saved["config"])
        model.load_state_dict(saved["model"])
        model.eval()
        print(decode(model.generate(encode(args.sample)[None], 300)[0]))
        return

    cfg = Config()
    model = Vitruvian(cfg)
    total = sum(p.numel() for p in model.parameters())
    print(f"Vitruvian-369: {total / 1e6:.2f}M parameters")

    data = torch.frombuffer(bytearray(load_corpus(args.data)), dtype=torch.uint8).long()
    split = int(len(data) * 0.95)
    train, val = data[:split], data[split:]
    print(f"corpus: {len(data) / 1e6:.2f}M bytes")

    def batch(src):
        i = torch.randint(len(src) - cfg.context - 1, (args.batch,))
        x = torch.stack([src[j:j + cfg.context] for j in i])
        y = torch.stack([src[j + 1:j + cfg.context + 1] for j in i])
        return x, y

    opts = build_optimizers(model, args.lr)
    base_lrs = [o.param_groups[0]["lr"] for o in opts]
    start = time.time()
    for step in range(1, args.steps + 1):
        # warmup then cosine decay
        frac = min(step / 50, 0.5 * (1 + math.cos(math.pi * step / args.steps)))
        for o, lr in zip(opts, base_lrs):
            o.param_groups[0]["lr"] = lr * max(frac, 0.05)

        model.train()
        _, loss = model(*batch(train))
        for o in opts:
            o.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        for o in opts:
            o.step()
        model.rebalance_experts()

        if step % 100 == 0 or step == 1:
            model.eval()
            with torch.no_grad():
                _, vloss = model(*batch(val))
            print(f"step {step:5d}  train {loss.item():.3f}  val {vloss.item():.3f}  "
                  f"({time.time() - start:.0f}s)")

    torch.save({"config": cfg, "model": model.state_dict()}, CKPT)
    print(f"saved {CKPT}")
    model.eval()
    print("\n--- sample ---")
    print(decode(model.generate(encode("def ")[None], 300)[0]))


if __name__ == "__main__":
    main()
