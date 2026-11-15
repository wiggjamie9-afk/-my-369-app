import React, { useState } from 'react';
import * as Clipboard from 'expo-clipboard';
import { Banner, Btn, Card, Chip, Field, Label, Md, Row, Screen } from '../components/UI';
import { friendlyError, runClaude } from '../claude';
import { BLUEPRINT_SYSTEM, BlueprintInput, blueprintUser, USE_CASES } from '../prompts';
import { uid, useStore } from '../store';

export default function BlueprintScreen({ goSettings }: { goSettings: () => void }) {
  const { apiKey, model, blueprints, addBlueprint } = useStore();
  const [inp, setInp] = useState<BlueprintInput>({ useCase: USE_CASES[6], goal: '', skills: '', hoursPerWeek: '', tools: '' });
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('');
  const [err, setErr] = useState('');
  const [viewId, setViewId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const set = (k: keyof BlueprintInput) => (v: string) => setInp((s) => ({ ...s, [k]: v }));
  const current = blueprints.find((b) => b.id === viewId) ?? null;

  async function generate() {
    setErr('');
    setBusy(true);
    try {
      const r = await runClaude({ apiKey, model, system: BLUEPRINT_SYSTEM, user: blueprintUser(inp), onStatus: setStatus });
      const b = { id: uid(), createdAt: Date.now(), title: `${inp.useCase} team`, model, text: r.text };
      addBlueprint(b);
      setViewId(b.id);
    } catch (e) {
      setErr(friendlyError(e));
    } finally {
      setBusy(false);
      setStatus('');
    }
  }

  async function copy(text: string) {
    await Clipboard.setStringAsync(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  if (current) {
    return (
      <Screen title="BLUEPRINT" subtitle={`${current.title} · ${new Date(current.createdAt).toLocaleDateString()} · ${current.model}`}>
        <Row>
          <Btn title="Back" kind="ghost" onPress={() => setViewId(null)} />
          <Btn title={copied ? 'Copied' : 'Copy'} kind="ghost" onPress={() => copy(current.text)} />
        </Row>
        <Card style={{ marginTop: 12 }}><Md text={current.text} /></Card>
      </Screen>
    );
  }

  return (
    <Screen title="AI TEAM BLUEPRINT" subtitle="Answer five quick questions. Claude designs a lean 3-5 agent team with prompts, workflow, tools, QA and a 7-day launch plan.">
      {!apiKey ? (
        <Banner kind="warn">No API key yet. Add one in Settings to generate.</Banner>
      ) : null}
      {!apiKey ? <Btn title="Open Settings" kind="ghost" onPress={goSettings} style={{ marginBottom: 12 }} /> : null}

      <Card>
        <Label>Best first use case</Label>
        <Row wrap>{USE_CASES.map((u) => <Chip key={u} label={u} on={inp.useCase === u} onPress={() => set('useCase')(u)} />)}</Row>
        <Field label="What should the team help you do first?" value={inp.goal} onChangeText={set('goal')} multiline placeholder="e.g. find freelance clients and write outreach" />
        <Field label="Your skills" value={inp.skills} onChangeText={set('skills')} placeholder="e.g. sales, some Python, design" />
        <Field label="Hours per week" value={inp.hoursPerWeek} onChangeText={set('hoursPerWeek')} placeholder="e.g. 8" keyboardType="numeric" />
        <Field label="Tools you already use" value={inp.tools} onChangeText={set('tools')} placeholder="e.g. Notion, Gmail, Google Sheets" />
        {err ? <Banner kind="error">{err}</Banner> : null}
        <Btn title={busy ? status || 'Working...' : 'Generate blueprint'} onPress={generate} busy={busy} disabled={!apiKey} />
      </Card>

      {blueprints.length ? <Label>Saved blueprints</Label> : null}
      {blueprints.map((b) => (
        <Card key={b.id}>
          <Row>
            <Btn title="Open" kind="ghost" onPress={() => setViewId(b.id)} />
            <Label>{b.title} · {new Date(b.createdAt).toLocaleDateString()}</Label>
          </Row>
        </Card>
      ))}
    </Screen>
  );
}
