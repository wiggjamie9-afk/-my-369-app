import React, { useState } from 'react';
import * as Clipboard from 'expo-clipboard';
import { Alert, Platform } from 'react-native';
import { Banner, Btn, Card, Chip, Field, H, Label, P, Row, Screen } from '../components/UI';
import { testKey } from '../claude';
import { MODELS } from '../data/models';
import { useStore } from '../store';

export default function SettingsScreen() {
  const { apiKey, setApiKey, model, setModel, exportAll, clearAll, reports } = useStore();
  const [draft, setDraft] = useState('');
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const spent = reports.reduce((n, r) => n + r.costUsd, 0);

  async function save() {
    await setApiKey(draft);
    setDraft('');
    setMsg(draft.trim() ? 'Saved on this device.' : 'Key removed.');
  }
  async function check() {
    setBusy(true);
    setMsg(await testKey(apiKey));
    setBusy(false);
  }
  function wipe() {
    const go = () => clearAll().then(() => setMsg('Local data cleared.'));
    if (Platform.OS === 'web') return void (window.confirm('Delete all saved progress, reports and blueprints?') && go());
    Alert.alert('Delete all data?', 'Progress, reports and blueprints on this device will be removed.', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: go },
    ]);
  }

  return (
    <Screen title="SETTINGS" subtitle="Your key stays on this device and is sent only to Anthropic.">
      <Card>
        <H>Anthropic API key</H>
        <P muted>Status: {apiKey ? `saved (ends ...${apiKey.slice(-4)})` : 'not set'}</P>
        <Field value={draft} onChangeText={setDraft} secure placeholder="sk-ant-..." />
        <Row>
          <Btn title="Save key" onPress={save} disabled={!draft.trim()} />
          <Btn title="Test key" kind="ghost" onPress={check} busy={busy} disabled={!apiKey} />
          {apiKey ? <Btn title="Remove" kind="danger" onPress={() => setApiKey('').then(() => setMsg('Key removed.'))} /> : null}
        </Row>
        {msg ? <P small muted>{msg}</P> : null}
        <Banner kind="warn">
          Personal-use mode: the app calls Anthropic directly with your own key (stored in the iOS Keychain / Android Keystore). Do not ship this build to other people. A public app needs a backend that holds the key.
        </Banner>
      </Card>

      <Card>
        <H>Model</H>
        {MODELS.map((m) => (
          <Row key={m.id}>
            <Chip label={m.label} on={model === m.id} onPress={() => setModel(m.id)} />
            <P small muted>{m.note} · ${m.inPer1M}/${m.outPer1M} per 1M tokens</P>
          </Row>
        ))}
        <P small muted>Prices are list-price estimates. Research runs also pay per web search.</P>
      </Card>

      <Card>
        <H>Usage</H>
        <P>{reports.length} research runs · about ${spent.toFixed(2)} in tokens (estimate)</P>
        <Label>Your data</Label>
        <Row>
          <Btn title="Copy all as JSON" kind="ghost" onPress={() => Clipboard.setStringAsync(exportAll()).then(() => setMsg('Copied.'))} />
          <Btn title="Delete all" kind="danger" onPress={wipe} />
        </Row>
      </Card>
    </Screen>
  );
}
