import React, { useState } from 'react';
import { Text, View } from 'react-native';
import { Banner, Btn, Card, Chip, Field, H, Label, Link, P, Row, Screen } from '../components/UI';
import { IdeaView } from '../components/IdeaView';
import { friendlyError, runClaude } from '../claude';
import { buildReport } from '../parseReport';
import { RESEARCH_SYSTEM, ResearchInput, researchUser } from '../prompts';
import { useStore } from '../store';
import { MODELS } from '../data/models';
import { C } from '../theme';
import { PASS_SCORE, Report, totalScore } from '../types';

export default function ResearchScreen({ goSettings }: { goSettings: () => void }) {
  const { apiKey, model, addReport, reports, updateIdea } = useStore();
  const [inp, setInp] = useState<ResearchInput>({ niche: '', skills: '', budget: '', hoursPerWeek: '', audience: 'Both', avoid: '', minScore: PASS_SCORE });
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('');
  const [err, setErr] = useState('');
  const [viewId, setViewId] = useState<string | null>(null);
  const set = (k: keyof ResearchInput) => (v: string) => setInp((s) => ({ ...s, [k]: v }));
  const modelLabel = MODELS.find((m) => m.id === model)?.label ?? model;
  const report: Report | undefined = reports.find((r) => r.id === viewId);

  async function run() {
    setErr('');
    setBusy(true);
    try {
      const r = await runClaude({
        apiKey, model, system: RESEARCH_SYSTEM, user: researchUser(inp),
        webSearch: true, maxSearches: 25, maxTokens: 16000, onStatus: setStatus,
      });
      const rep = buildReport(inp.niche.trim(), model, r);
      addReport(rep);
      setViewId(rep.id);
    } catch (e) {
      setErr(friendlyError(e));
    } finally {
      setBusy(false);
      setStatus('');
    }
  }

  if (report) {
    return (
      <Screen title="RESEARCH REPORT" subtitle={`${report.niche} · ${new Date(report.createdAt).toLocaleString()} · ${report.model}`}>
        <Btn title="Back" kind="ghost" onPress={() => setViewId(null)} style={{ marginBottom: 12 }} />
        <Banner kind="info">
          {report.searches} web searches · {report.inTokens.toLocaleString()} in / {report.outTokens.toLocaleString()} out tokens · about ${report.costUsd.toFixed(2)} in tokens (web search fees are extra). Ideas are saved in the Ideas tab.
        </Banner>
        {report.raw ? (
          <Card>
            <H>Could not structure the output</H>
            <P muted>The model's answer did not parse into ideas. Raw text below. Try again, or use a stronger model.</P>
            <P>{report.raw}</P>
          </Card>
        ) : null}
        {report.marketMap.length ? (
          <Card>
            <H>Market map</H>
            {report.marketMap.map((l, i) => <P key={i}>• {l}</P>)}
          </Card>
        ) : null}
        {report.strongestQuote ? (
          <Card>
            <Label>Strongest quote</Label>
            <P>"{report.strongestQuote.text}"</P>
            {report.strongestQuote.url ? <Link url={report.strongestQuote.url}>{report.strongestQuote.url}</Link> : null}
          </Card>
        ) : null}
        {report.ideas.length === 0 && !report.raw ? <Banner kind="warn">No ideas passed the evidence bar. That can be the right answer. Try a narrower niche.</Banner> : null}
        {report.ideas.map((idea) => (
          <View key={idea.id} style={{ marginBottom: 24 }}>
            <Text style={{ color: C.muted, fontSize: 11, marginBottom: 6 }}>
              {totalScore(idea.scores) >= PASS_SCORE ? 'PASSES THE BAR' : 'BELOW THE BAR'}
            </Text>
            <IdeaView
              idea={idea}
              onStatus={(s) => updateIdea(report.id, idea.id, { status: s })}
              onNotes={(n) => updateIdea(report.id, idea.id, { notes: n })}
            />
          </View>
        ))}
      </Screen>
    );
  }

  return (
    <Screen title="MARKET RESEARCH" subtitle="Claude searches the live web for what real people complain about, then finds gaps nobody covers. One run takes a few minutes.">
      {!apiKey ? (
        <>
          <Banner kind="warn">No API key yet. Add one in Settings to run research.</Banner>
          <Btn title="Open Settings" kind="ghost" onPress={goSettings} style={{ marginBottom: 12 }} />
        </>
      ) : null}
      <Card>
        <Field label="Niche or industries to research" value={inp.niche} onChangeText={set('niche')} multiline placeholder="e.g. freelance designers, independent gyms, dental practices" />
        <Field label="Your skills" value={inp.skills} onChangeText={set('skills')} placeholder="e.g. mobile apps, copywriting" />
        <Field label="Budget" value={inp.budget} onChangeText={set('budget')} placeholder="e.g. under £500" />
        <Field label="Hours per week" value={inp.hoursPerWeek} onChangeText={set('hoursPerWeek')} placeholder="e.g. 10" keyboardType="numeric" />
        <Label>Customers</Label>
        <Row wrap>{(['B2B', 'B2C', 'Both'] as const).map((a) => <Chip key={a} label={a} on={inp.audience === a} onPress={() => setInp((s) => ({ ...s, audience: a }))} />)}</Row>
        <Field label="Markets you never want to see" value={inp.avoid} onChangeText={set('avoid')} placeholder="e.g. crypto, gambling" />
        {err ? <Banner kind="error">{err}</Banner> : null}
        <P small muted>Model: {modelLabel}. A run can use up to 25 web searches; see the cost note on the report. Change model in Settings.</P>
        <Btn title={busy ? status || 'Researching...' : 'Run research'} onPress={run} busy={busy} disabled={!apiKey || !inp.niche.trim()} />
        {busy ? <P small muted>Keep the app open. This usually takes 2-6 minutes.</P> : null}
      </Card>

      {reports.length ? <Label>Past reports</Label> : null}
      {reports.map((r) => (
        <Card key={r.id}>
          <Row>
            <Btn title="Open" kind="ghost" onPress={() => setViewId(r.id)} />
            <View style={{ flex: 1 }}>
              <P>{r.niche}</P>
              <P small muted>{new Date(r.createdAt).toLocaleDateString()} · {r.ideas.length} ideas · ${r.costUsd.toFixed(2)}</P>
            </View>
          </Row>
        </Card>
      ))}
    </Screen>
  );
}
