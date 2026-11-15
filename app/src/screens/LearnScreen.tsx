import React, { useState } from 'react';
import { Text, View } from 'react-native';
import { Card, Chip, Link, P, Row, Screen } from '../components/UI';
import { CONCEPTS, STEPS, WEEKS } from '../data/roadmap';
import { useStore } from '../store';
import { C, S } from '../theme';

export default function LearnScreen() {
  const { progress, toggleStep } = useStore();
  const [tab, setTab] = useState<'plan' | 'concepts'>('plan');
  const total = WEEKS.length * STEPS.length;
  const done = WEEKS.reduce((n, w) => n + STEPS.filter((_, i) => progress[`w${w.n}:${i}`]).length, 0);
  const pct = Math.round((done / total) * 100);

  return (
    <Screen title="LEARN" subtitle="12-week AI engineer plan, built from the roadmap you saved. 10-15 hours a week, Python basics assumed.">
      <Row>
        <Chip label="12-week plan" on={tab === 'plan'} onPress={() => setTab('plan')} />
        <Chip label="Agent concepts" on={tab === 'concepts'} onPress={() => setTab('concepts')} />
      </Row>

      {tab === 'plan' ? (
        <>
          <Card>
            <Row>
              <Text style={{ color: C.gold, fontSize: 30, fontWeight: '700' }}>{pct}%</Text>
              <Text style={{ color: C.muted }}>{done} of {total} steps done</Text>
            </Row>
            <View style={{ height: 8, backgroundColor: C.border, borderRadius: 4, marginTop: S.sm }}>
              <View style={{ height: 8, width: `${pct}%`, backgroundColor: C.purple, borderRadius: 4 }} />
            </View>
          </Card>
          {WEEKS.map((w) => {
            const wd = STEPS.filter((_, i) => progress[`w${w.n}:${i}`]).length;
            return (
              <Card key={w.n}>
                <Text style={{ color: C.muted, fontSize: 11, letterSpacing: 1 }}>WEEK {w.n} · {w.source.toUpperCase()}</Text>
                <Text style={{ color: C.text, fontSize: 17, fontWeight: '600', marginVertical: 4 }}>{w.title}</Text>
                <P muted>{w.goal}</P>
                <P small muted>Project: {w.project}</P>
                <View style={{ marginVertical: S.sm }}>
                  {STEPS.map((s, i) => {
                    const on = !!progress[`w${w.n}:${i}`];
                    return (
                      <Text key={s} onPress={() => toggleStep(`w${w.n}:${i}`)} style={{ color: on ? C.good : C.text, fontSize: 15, paddingVertical: 6 }}>
                        {on ? '☑' : '☐'}  {s}
                      </Text>
                    );
                  })}
                </View>
                <Row>
                  <Link url={w.url}>Open course</Link>
                  <Text style={{ color: C.muted, fontSize: 12 }}>  {wd}/{STEPS.length}</Text>
                </Row>
              </Card>
            );
          })}
        </>
      ) : (
        <View style={{ marginTop: S.md }}>
          {CONCEPTS.map((c) => (
            <Card key={c.term}>
              <Text style={{ color: C.gold, fontWeight: '600', fontSize: 15, marginBottom: 2 }}>{c.term}</Text>
              <P>{c.def}</P>
            </Card>
          ))}
        </View>
      )}
    </Screen>
  );
}
