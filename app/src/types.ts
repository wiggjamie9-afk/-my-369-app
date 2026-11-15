export type Scores = {
  frequency: number;
  intensity: number;
  willingness: number;
  reachability: number;
  buildability: number;
};

export type Quote = {
  text: string;
  url: string;
  source?: string;
  date?: string;
  /** Set by the app: was this URL present in the live web search results? */
  seen?: boolean;
};

export type IdeaStatus = 'new' | 'testing' | 'validated' | 'dropped';

export type Idea = {
  id: string;
  name: string;
  pitch: string;
  gap: string;
  who: string;
  quotes: Quote[];
  scores: Scores;
  competitors: { name: string; whyMissed: string; url?: string }[];
  pricing: string;
  mvp: { coreFeature: string; skip: string; stack: string; plan: string[] };
  firstCustomers: string;
  risk: string;
  cheapestTest: string;
  whatWouldKill: string;
  status: IdeaStatus;
  notes: string;
};

export type Report = {
  id: string;
  createdAt: number;
  niche: string;
  model: string;
  marketMap: string[];
  strongestQuote?: Quote;
  ideas: Idea[];
  searches: number;
  inTokens: number;
  outTokens: number;
  costUsd: number;
  raw?: string; // kept when JSON parsing failed
};

export type Blueprint = {
  id: string;
  createdAt: number;
  title: string;
  model: string;
  text: string;
};

export const SCORE_KEYS: (keyof Scores)[] = ['frequency', 'intensity', 'willingness', 'reachability', 'buildability'];
export const PASS_SCORE = 18;

export function totalScore(s: Scores): number {
  return SCORE_KEYS.reduce((sum, k) => sum + clamp(Number(s?.[k]) || 0), 0);
}
function clamp(n: number) {
  return Math.max(1, Math.min(5, Math.round(n)));
}
