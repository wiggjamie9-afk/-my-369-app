# Panel Mate

Test a product idea on a panel of simulated Australian customers (default 1,000), then see who
would buy, who would pass, why, and at what price.

**What it is good for:** finding objections, weak pitches and price problems cheaply, before you
spend money.
**What it cannot do:** tell you how many real people will buy. Simulated customers are not real
customers. Models tend to be polite and agreeable, so a panel can say "yes" far more than the real
world does. Treat the numbers as a way to compare two versions of an idea, not as a forecast.

## How it works
- The 1,000 customers (age, state, household, income, shopping style) are drawn by the program from a
  seeded random generator, so the mix is controlled and repeatable. The model does not invent them.
  The weights are illustrative and Australian-shaped, not census-exact.
- Each customer is one model call. They are told that real people say no to most offers.
- A **control check** runs 200 of the same customers on a deliberately bad offer (an empty box at
  5x your price). If they say BUY or MAYBE to it more than about 20% of the time, the report shows a
  warning: the panel is too agreeable and the results are noise.
- Output: `report.html` (phone-friendly), `summary.json`, `answers.csv`.
- Stops cleanly on a bad key, retries rate limits, and resumes if interrupted.

## Try it free (fake answers, to see the report)
```
python3 panel.py run examples/snack-box.json --mock
```
Mock answers are made up by the program and the report says so in red.

## Run it for real
1. Get an Anthropic API key and set it: `export ANTHROPIC_API_KEY=...` (never put it in a file).
2. Copy `examples/snack-box.json`, edit name, pitch and price.
3. `python3 panel.py run my-idea.json --size 1000 --yes`

A 1,000 run is 1,200 model calls. **That spends your money.** Check Anthropic's current pricing first.
The program will not run without `--yes`, and refuses more than `--max-calls` (default 2,500).
Start with `--size 100` to see how it behaves.

Default model is `claude-haiku-5-5` (cheapest). Change with `--model`.

## A 10,000-customer panel
```
python3 panel.py run my-idea.json --size 10000 --workers 24 --max-calls 10500 --yes
```
- That is 10,000 customers plus a 500-customer control check = **10,500 model calls, about 9 times a 1,000 run**. The `--max-calls` flag is a deliberate safety catch: you have to raise it on purpose. Check Anthropic's pricing and set a spending limit on your API account first.
- Time depends on your account's rate limits. As a rough guess (not measured), 10,500 calls at 24 at a time is under an hour. If it stops, run the same command again: it resumes where it left off and does not pay twice for answers it already has.
- Do a `--size 100` run first, then a 1,000 run, then 10,000.
- **What 10,000 buys you:** a tighter result (about 0.5 points of simulation noise instead of about 1.5) and groups big enough to read, such as one state or age band. **What it does not buy you:** accuracy. A bigger panel of the same simulated customers repeats the same biases, so 10,000 simulated people are still not 10,000 real ones.

## Using it well
- Run it twice with two versions of your pitch or price and compare. The difference matters more than the level.
- Read the "why people said no" and the quotes. That is where the value is.
- Then test with 5 to 10 real people before you spend anything. A simulated panel cannot replace that.

## Swarm 1001: check a whole business, not just the pitch
`swarm.py` is the full check. **1,000 customers + 1 judge = 1,001 nodes**, plus the extras below.
For apps and software it simulates **small-business owners** (tradies and similar) instead of shoppers,
because general shoppers are the wrong test for tradie software.

| Part | What it does | AI? |
|---|---|---|
| Customers (1,000) | Simulated buyers or business owners say BUY / MAYBE / PASS and why | yes |
| Control check | Same panel on a deliberately bad offer; flags an over-agreeable panel | yes |
| Money check | GST, fees, refunds, postage, ad cost, break-even, and for subscriptions lifetime value vs cost to win a customer. Whole cents, no floats | **no, plain maths** |
| Red team, claims auditor, compliance flagger, pricing critic, clarity | Five specialists, one call each | yes, unverified opinions |
| Review reader (optional) | Reads REAL competitor reviews you supply (`reviews_file`, one per line) in batches of 40 | yes, on real data |
| Judge (1) | Writes the plain-English summary. It cannot change the verdict | yes |

**The verdict is decided by fixed rules, not the AI.** In order: INCOMPLETE (missing cost numbers), STOP (you lose money per
order, or a customer is worth less than they cost to win), UNRELIABLE (control check failed or didn't run), HOLD (a medium or
high confidence serious compliance flag), FIX (under 3% would buy), PROMISING. The 3% and the compliance cut-off are rules of
thumb in `swarm.py`; change them if you disagree. **It never says "go".** PROMISING means "test with 5 to 10 real people".

```
python3 swarm.py run examples/businesses/snack-box.json --mock        # free, fake AI answers, real maths
python3 swarm.py batch examples/businesses --mock                     # every business in a folder, ranked
ANTHROPIC_API_KEY=... python3 swarm.py batch my-businesses --yes --max-calls 10000
```
Business file fields: `name, pitch, price` (required), `type` (`product` or `subscription`, where price is per month),
`audience` (`consumer` or `business`), `details`, the cost fields shown in `examples/businesses/`, and optional `reviews_file`.
**Costs are entered ex-GST. The example numbers are placeholders: replace them with your real ones.** The sample snack box
returns STOP because those placeholder costs lose $6.09 an order; that is the maths working, not a bug.

Calls per business: customers + control + 5 specialists + review batches + 1 judge. The guard counts all of them across a batch
before it spends anything. Specialist and review results are cached, so a re-run only pays for the judge.

What the money check does not do: it does not know your real costs, tax position or competitors, and the refund and
payment-fee treatment is simplified. The compliance specialist is not a lawyer.

## Tests
`python3 -m unittest discover -s tests` (35 tests, including a fake API server for retries, key errors and call counts).
Real model answers have not been tested here, because no API key was available.
