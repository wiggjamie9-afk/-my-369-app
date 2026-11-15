import React from 'react';
import { Text, View } from 'react-native';
import { C, S } from '../theme';
import { Idea, IdeaStatus, PASS_SCORE, SCORE_KEYS, totalScore } from '../types';
import { Btn, Card, Chip, Field, H, Label, Link, P, Row } from './UI';

const STATUSES: IdeaStatus[] = ['new', 'testing', 'validated', 'dropped'];

export function ScoreBar({ idea }: { idea: Idea }) {
  const total = totalScore(idea.scores);
  const col = total >= PASS_SCORE ? C.good : total >= 14 ? C.warn : C.bad;
  return (
    <View>
      <Row>
        <Text style={{ color: col, fontSize: 28, fontWeight: '700' }}>{total}</Text>
        <Text style={{ color: C.muted }}>/ 25 pain score</Text>
      </Row>
      <View style={{ marginTop: S.sm }}>
        {SCORE_KEYS.map((k) => (
          <View key={k} style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 4 }}>
            <Text style={{ color: C.muted, width: 100, fontSize: 12 }}>{k}</Text>
            <View style={{ flexDirection: 'row' }}>
              {[1, 2, 3, 4, 5].map((n) => (
                <View key={n} style={{ width: 22, height: 8, marginRight: 3, borderRadius: 2, backgroundColor: n <= (idea.scores[k] || 0) ? col : C.border }} />
              ))}
            </View>
          </View>
        ))}
      </View>
      <P small muted>Total is computed by the app from the five scores. Scores are the model's estimates.</P>
    </View>
  );
}

export function IdeaView({
  idea, onStatus, onNotes,
}: { idea: Idea; onStatus?: (s: IdeaStatus) => void; onNotes?: (n: string) => void }) {
  const real = idea.quotes.filter((q) => q.seen).length;
  return (
    <View>
      <Card>
        <Text style={{ color: C.gold, fontSize: 20, fontWeight: '600' }}>{idea.name}</Text>
        <P>{idea.pitch}</P>
        <ScoreBar idea={idea} />
      </Card>

      {onStatus ? (
        <Card>
          <Label>Status</Label>
          <Row wrap>
            {STATUSES.map((s) => <Chip key={s} label={s} on={idea.status === s} onPress={() => onStatus(s)} />)}
          </Row>
          {onNotes ? <Field label="Notes" value={idea.notes} onChangeText={onNotes} multiline placeholder="What did you learn testing this?" /> : null}
        </Card>
      ) : null}

      <Card>
        <H>The gap</H>
        <P>{idea.gap}</P>
        <Label>Who has the pain</Label>
        <P>{idea.who}</P>
      </Card>

      <Card>
        <H>Proof (quotes)</H>
        <P small muted>
          {real} of {idea.quotes.length} quote links appeared in the live search results. A link marked "not verified" may still be real, open it before you trust it.
        </P>
        {idea.quotes.map((q, i) => (
          <View key={i} style={{ marginTop: S.sm, borderLeftWidth: 2, borderLeftColor: q.seen ? C.good : C.warn, paddingLeft: S.md }}>
            <P>"{q.text}"</P>
            <P small muted>
              {q.source || 'source'}{q.date ? ` · ${q.date}` : ''} · {q.seen ? 'found in search' : 'not verified'}
            </P>
            {q.url ? <Link url={q.url}>{q.url.length > 60 ? q.url.slice(0, 60) + '…' : q.url}</Link> : null}
          </View>
        ))}
      </Card>

      <Card>
        <H>Competitors and why they miss</H>
        {idea.competitors.map((c, i) => (
          <View key={i} style={{ marginBottom: S.sm }}>
            <P><Text style={{ fontWeight: '700' }}>{c.name}</Text>: {c.whyMissed}</P>
            {c.url ? <Link url={c.url}>{c.url}</Link> : null}
          </View>
        ))}
        <Label>Pricing (estimate)</Label>
        <P>{idea.pricing}</P>
      </Card>

      <Card>
        <H>MVP plan</H>
        <Label>Core feature</Label><P>{idea.mvp.coreFeature}</P>
        <Label>Skip for now</Label><P>{idea.mvp.skip}</P>
        <Label>Stack</Label><P>{idea.mvp.stack}</P>
        <Label>14-day plan</Label>
        {idea.mvp.plan.map((s, i) => <P key={i}>{i + 1}. {s}</P>)}
      </Card>

      <Card>
        <H>Go to market</H>
        <Label>First 10 customers</Label><P>{idea.firstCustomers}</P>
        <Label>Biggest risk</Label><P>{idea.risk}</P>
        <Label>Cheapest test this week</Label><P>{idea.cheapestTest}</P>
      </Card>

      <Card style={{ borderColor: C.bad }}>
        <H>What would kill this idea?</H>
        <P>{idea.whatWouldKill}</P>
      </Card>
    </View>
  );
}

export { Btn };
