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

A full run is 1,200 model calls. **That spends your money.** Check Anthropic's current pricing first.
The program will not run without `--yes`, and refuses more than `--max-calls` (default 2,500).
Start with `--size 100` to see how it behaves.

Default model is `claude-haiku-5-5` (cheapest). Change with `--model`.

## Using it well
- Run it twice with two versions of your pitch or price and compare. The difference matters more than the level.
- Read the "why people said no" and the quotes. That is where the value is.
- Then test with 5 to 10 real people before you spend anything. A simulated panel cannot replace that.

## Tests
`python3 -m unittest discover -s tests` (19 tests, including a fake API server for retries and key errors).
Real model answers have not been tested here, because no API key was available.
