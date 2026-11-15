import React, { useMemo, useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { Btn, Card, Chip, P, Row, Screen } from '../components/UI';
import { IdeaView } from '../components/IdeaView';
import { useStore } from '../store';
import { C } from '../theme';
import { IdeaStatus, totalScore } from '../types';

const FILTERS: ('all' | IdeaStatus)[] = ['all', 'new', 'testing', 'validated', 'dropped'];

export default function IdeasScreen() {
  const { reports, updateIdea } = useStore();
  const [filter, setFilter] = useState<'all' | IdeaStatus>('all');
  const [open, setOpen] = useState<{ r: string; i: string } | null>(null);

  const rows = useMemo(
    () => reports.flatMap((r) => r.ideas.map((i) => ({ r, i }))).filter((x) => filter === 'all' || x.i.status === filter)
      .sort((a, b) => totalScore(b.i.scores) - totalScore(a.i.scores)),
    [reports, filter],
  );
  const sel = open ? rows.find((x) => x.r.id === open.r && x.i.id === open.i) ?? reports.flatMap((r) => r.ideas.map((i) => ({ r, i }))).find((x) => x.r.id === open.r && x.i.id === open.i) : undefined;

  if (sel) {
    return (
      <Screen title="IDEA" subtitle={`From: ${sel.r.niche}`}>
        <Btn title="Back" kind="ghost" onPress={() => setOpen(null)} style={{ marginBottom: 12 }} />
        <IdeaView
          idea={sel.i}
          onStatus={(s) => updateIdea(sel.r.id, sel.i.id, { status: s })}
          onNotes={(n) => updateIdea(sel.r.id, sel.i.id, { notes: n })}
        />
      </Screen>
    );
  }

  return (
    <Screen title="IDEAS" subtitle="Every idea from every research run, best score first. Track which ones you are testing.">
      <Row wrap>{FILTERS.map((f) => <Chip key={f} label={f} on={filter === f} onPress={() => setFilter(f)} />)}</Row>
      {rows.length === 0 ? <Card><P muted>No ideas yet. Run a research report first.</P></Card> : null}
      {rows.map(({ r, i }) => (
        <Pressable key={i.id} onPress={() => setOpen({ r: r.id, i: i.id })}>
          <Card>
            <Row>
              <Text style={{ color: C.gold, fontSize: 24, fontWeight: '700', width: 44 }}>{totalScore(i.scores)}</Text>
              <View style={{ flex: 1 }}>
                <Text style={{ color: C.text, fontSize: 16, fontWeight: '600' }}>{i.name}</Text>
                <P small muted>{i.pitch}</P>
                <P small muted>{i.status} · {r.niche}</P>
              </View>
            </Row>
          </Card>
        </Pressable>
      ))}
    </Screen>
  );
}
