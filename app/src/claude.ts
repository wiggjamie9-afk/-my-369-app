import { Platform } from 'react-native';
import Anthropic from '@anthropic-ai/sdk';
import { estimateCost, ModelId } from './data/models';

export type RunResult = {
  text: string;
  inTokens: number;
  outTokens: number;
  searches: number;
  /** URLs returned by live web searches (used to flag unverifiable quote links). */
  seenUrls: string[];
  costUsd: number;
};

type RunOpts = {
  apiKey: string;
  model: ModelId;
  system: string;
  user: string;
  webSearch?: boolean;
  maxSearches?: number;
  maxTokens?: number;
  onStatus?: (s: string) => void;
};

export function friendlyError(e: unknown): string {
  if (e instanceof Anthropic.AuthenticationError) return 'Your API key was rejected. Check it in Settings.';
  if (e instanceof Anthropic.PermissionDeniedError) return 'This key does not have access to that model or feature.';
  if (e instanceof Anthropic.RateLimitError) return 'Rate limited or out of credit. Wait a minute or check your Anthropic billing.';
  if (e instanceof Anthropic.APIConnectionError) return 'Could not reach Anthropic. Check your connection and try again.';
  if (e instanceof Anthropic.APIError) return `Anthropic API error (${e.status ?? '?'}): ${e.message}`;
  return e instanceof Error ? e.message : String(e);
}

export async function runClaude(o: RunOpts): Promise<RunResult> {
  const client = new Anthropic({
    apiKey: o.apiKey,
    // Needed for the web preview only. On iOS/Android this flag is unused.
    dangerouslyAllowBrowser: Platform.OS === 'web',
    timeout: 10 * 60 * 1000,
    maxRetries: 1,
  });

  const messages: any[] = [{ role: 'user', content: o.user }];
  const tools: any[] = o.webSearch
    ? [{ type: 'web_search_20260209', name: 'web_search', max_uses: o.maxSearches ?? 20 }]
    : [];

  let inTokens = 0;
  let outTokens = 0;
  let searches = 0;
  const seen = new Set<string>();
  let text = '';
  let useFallbacks = true;

  for (let turn = 0; turn < 6; turn++) {
    o.onStatus?.(turn === 0 ? 'Thinking and searching...' : `Still working (step ${turn + 1})...`);

    const params: any = {
      model: o.model,
      max_tokens: o.maxTokens ?? 16000,
      system: o.system,
      messages,
      ...(tools.length ? { tools } : {}),
    };

    let resp: any;
    try {
      // Refusal fallback is on by default for these models; if the API rejects it, retry without.
      resp = useFallbacks
        ? await (client.beta.messages as any).create({
            ...params,
            betas: ['server-side-fallback-2026-07-01'],
            fallbacks: 'default',
          })
        : await (client.messages as any).create(params);
    } catch (e) {
      if (useFallbacks && e instanceof Anthropic.BadRequestError) {
        useFallbacks = false;
        turn--;
        continue;
      }
      throw e;
    }

    inTokens += resp.usage?.input_tokens ?? 0;
    outTokens += resp.usage?.output_tokens ?? 0;
    searches += resp.usage?.server_tool_use?.web_search_requests ?? 0;

    for (const b of resp.content ?? []) {
      if (b.type === 'web_search_tool_result' && Array.isArray(b.content)) {
        for (const r of b.content) if (r?.url) seen.add(r.url);
      }
    }

    if (resp.stop_reason === 'refusal') {
      throw new Error('The model declined this request' + (resp.stop_details?.explanation ? `: ${resp.stop_details.explanation}` : '.'));
    }

    text = (resp.content ?? []).filter((b: any) => b.type === 'text').map((b: any) => b.text).join('\n');

    if (resp.stop_reason === 'pause_turn') {
      messages.push({ role: 'assistant', content: resp.content });
      continue;
    }
    if (resp.stop_reason === 'max_tokens') {
      text += '\n\n[Output was cut off at the token limit.]';
    }
    break;
  }

  return { text, inTokens, outTokens, searches, seenUrls: [...seen], costUsd: estimateCost(o.model, inTokens, outTokens) };
}

/** Cheap key check: one tiny request. */
export async function testKey(apiKey: string): Promise<string> {
  try {
    await runClaude({ apiKey, model: 'claude-haiku-5-5', system: 'Reply with OK.', user: 'ping', maxTokens: 64 });
    return 'Key works.';
  } catch (e) {
    return friendlyError(e);
  }
}
