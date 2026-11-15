import { Idea, Quote, Report } from './types';
import { uid } from './store';
import { estimateCost, ModelId } from './data/models';
import { RunResult } from './claude';

function extractJson(text: string): any | null {
  const fenced = [...text.matchAll(/```json\s*([\s\S]*?)```/gi)];
  const candidates: string[] = fenced.map((m) => m[1]);
  const a = text.indexOf('{');
  const b = text.lastIndexOf('}');
  if (a >= 0 && b > a) candidates.push(text.slice(a, b + 1));
  for (const c of candidates.reverse()) {
    try {
      return JSON.parse(c);
    } catch {
      /* try next */
    }
  }
  return null;
}

function norm(u: string) {
  return u.replace(/^https?:\/\/(www\.)?/, '').replace(/[#?].*$/, '').replace(/\/$/, '').toLowerCase();
}

function markSeen(q: Quote, seen: Set<string>): Quote {
  const n = norm(q?.url ?? '');
  return { ...q, text: String(q?.text ?? ''), url: String(q?.url ?? ''), seen: n ? seen.has(n) : false };
}

export function buildReport(niche: string, model: ModelId, run: RunResult): Report {
  const seen = new Set(run.seenUrls.map(norm));
  const json = extractJson(run.text);
  const base = {
    id: uid(),
    createdAt: Date.now(),
    niche,
    model,
    searches: run.searches,
    inTokens: run.inTokens,
    outTokens: run.outTokens,
    costUsd: estimateCost(model, run.inTokens, run.outTokens),
  };
  if (!json || !Array.isArray(json.ideas)) {
    return { ...base, marketMap: [], ideas: [], raw: run.text };
  }
  const ideas: Idea[] = json.ideas.map((x: any): Idea => ({
    id: uid(),
    name: String(x.name ?? 'Untitled'),
    pitch: String(x.pitch ?? ''),
    gap: String(x.gap ?? ''),
    who: String(x.who ?? ''),
    quotes: (Array.isArray(x.quotes) ? x.quotes : []).map((q: Quote) => markSeen(q, seen)),
    scores: {
      frequency: Number(x.scores?.frequency) || 1,
      intensity: Number(x.scores?.intensity) || 1,
      willingness: Number(x.scores?.willingness) || 1,
      reachability: Number(x.scores?.reachability) || 1,
      buildability: Number(x.scores?.buildability) || 1,
    },
    competitors: Array.isArray(x.competitors) ? x.competitors : [],
    pricing: String(x.pricing ?? ''),
    mvp: {
      coreFeature: String(x.mvp?.coreFeature ?? ''),
      skip: String(x.mvp?.skip ?? ''),
      stack: String(x.mvp?.stack ?? ''),
      plan: Array.isArray(x.mvp?.plan) ? x.mvp.plan.map(String) : [],
    },
    firstCustomers: String(x.firstCustomers ?? ''),
    risk: String(x.risk ?? ''),
    cheapestTest: String(x.cheapestTest ?? ''),
    whatWouldKill: String(x.whatWouldKill ?? ''),
    status: 'new',
    notes: '',
  }));
  return {
    ...base,
    marketMap: Array.isArray(json.marketMap) ? json.marketMap.map(String) : [],
    strongestQuote: json.strongestQuote?.text ? markSeen(json.strongestQuote, seen) : undefined,
    ideas,
  };
}
