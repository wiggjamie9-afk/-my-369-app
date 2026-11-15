// Model IDs and list prices (USD per 1M tokens). Prices are cached estimates,
// check Anthropic's pricing page before relying on them.
export type ModelId =
  | 'claude-opus-5-5'
  | 'claude-sonnet-5-5'
  | 'claude-fable-5-2'
  | 'claude-haiku-5-5';

export const MODELS: { id: ModelId; label: string; note: string; inPer1M: number; outPer1M: number }[] = [
  { id: 'claude-opus-5-5', label: 'Opus 5.5', note: 'Best default: strong and mid-priced', inPer1M: 4, outPer1M: 20 },
  { id: 'claude-sonnet-5-5', label: 'Sonnet 5.5', note: 'Cheaper, fast, good for blueprints', inPer1M: 2, outPer1M: 10 },
  { id: 'claude-fable-5-2', label: 'Fable 5.2', note: 'Most capable, most expensive', inPer1M: 8, outPer1M: 40 },
  { id: 'claude-haiku-5-5', label: 'Haiku 5.5', note: 'Cheapest, for testing the app', inPer1M: 0.1, outPer1M: 0.5 },
];

export const DEFAULT_MODEL: ModelId = 'claude-opus-5-5';

export function estimateCost(model: ModelId, inTok: number, outTok: number): number {
  const m = MODELS.find((x) => x.id === model) ?? MODELS[0];
  return (inTok / 1e6) * m.inPer1M + (outTok / 1e6) * m.outPer1M;
}
