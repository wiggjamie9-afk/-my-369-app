import React from 'react';
import { ActivityIndicator, Linking, Pressable, ScrollView, StyleProp, StyleSheet, Text, TextInput, View, ViewStyle } from 'react-native';
import { C, S } from '../theme';

export function Screen({ children, title, subtitle }: { children: React.ReactNode; title: string; subtitle?: string }) {
  return (
    <ScrollView style={{ flex: 1 }} contentContainerStyle={st.screen} keyboardShouldPersistTaps="handled">
      <Text style={st.title}>{title}</Text>
      {subtitle ? <Text style={st.subtitle}>{subtitle}</Text> : null}
      {children}
      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

export function Card({ children, style }: { children: React.ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[st.card, style]}>{children}</View>;
}

export function H({ children }: { children: React.ReactNode }) {
  return <Text style={st.h}>{children}</Text>;
}

export function P({ children, muted, small }: { children: React.ReactNode; muted?: boolean; small?: boolean }) {
  return <Text style={[st.p, muted && { color: C.muted }, small && { fontSize: 12 }]}>{children}</Text>;
}

export function Label({ children }: { children: React.ReactNode }) {
  return <Text style={st.label}>{children}</Text>;
}

export function Btn({
  title, onPress, kind = 'primary', disabled, busy, style,
}: { title: string; onPress: () => void; kind?: 'primary' | 'ghost' | 'danger'; disabled?: boolean; busy?: boolean; style?: StyleProp<ViewStyle> }) {
  const off = disabled || busy;
  return (
    <Pressable
      onPress={off ? undefined : onPress}
      style={({ pressed }) => [
        st.btn,
        kind === 'primary' && { backgroundColor: C.purple },
        kind === 'ghost' && { backgroundColor: 'transparent', borderWidth: 1, borderColor: C.border },
        kind === 'danger' && { backgroundColor: 'transparent', borderWidth: 1, borderColor: C.bad },
        off && { opacity: 0.5 },
        pressed && { opacity: 0.8 },
        style,
      ]}
    >
      {busy ? <ActivityIndicator color={C.text} /> : <Text style={[st.btnText, kind === 'danger' && { color: C.bad }]}>{title}</Text>}
    </Pressable>
  );
}

export function Chip({ label, on, onPress }: { label: string; on?: boolean; onPress?: () => void }) {
  return (
    <Pressable onPress={onPress} style={[st.chip, on && { borderColor: C.gold, backgroundColor: '#2a2215' }]}>
      <Text style={[st.chipText, on && { color: C.gold }]}>{label}</Text>
    </Pressable>
  );
}

export function Field({
  label, value, onChangeText, placeholder, multiline, secure, keyboardType,
}: { label?: string; value: string; onChangeText: (t: string) => void; placeholder?: string; multiline?: boolean; secure?: boolean; keyboardType?: 'default' | 'numeric' }) {
  return (
    <View style={{ marginBottom: S.md }}>
      {label ? <Label>{label}</Label> : null}
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={C.muted}
        multiline={multiline}
        secureTextEntry={secure}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType={keyboardType}
        style={[st.input, multiline && { minHeight: 80, textAlignVertical: 'top' }]}
      />
    </View>
  );
}

export function Row({ children, wrap }: { children: React.ReactNode; wrap?: boolean }) {
  return <View style={{ flexDirection: 'row', flexWrap: wrap ? 'wrap' : 'nowrap', gap: S.sm, alignItems: 'center' }}>{children}</View>;
}

export function Link({ url, children }: { url: string; children: React.ReactNode }) {
  return (
    <Text style={{ color: C.gold, textDecorationLine: 'underline' }} onPress={() => Linking.openURL(url).catch(() => {})}>
      {children}
    </Text>
  );
}

export function Banner({ kind, children }: { kind: 'info' | 'warn' | 'error'; children: React.ReactNode }) {
  const col = kind === 'error' ? C.bad : kind === 'warn' ? C.warn : C.purple;
  return (
    <View style={[st.banner, { borderColor: col }]}>
      <Text style={{ color: C.text, fontSize: 13, lineHeight: 19 }}>{children}</Text>
    </View>
  );
}

/** Tiny Markdown renderer: headings, bullets, numbered lists, tables (as text), code fences, bold, inline code. */
export function Md({ text }: { text: string }) {
  const lines = text.split('\n');
  const out: React.ReactNode[] = [];
  let code: string[] | null = null;
  lines.forEach((ln, i) => {
    if (ln.trim().startsWith('```')) {
      if (code) {
        out.push(<View key={i} style={st.code}><Text selectable style={st.codeText}>{code.join('\n')}</Text></View>);
        code = null;
      } else code = [];
      return;
    }
    if (code) { code.push(ln); return; }
    const h = /^(#{1,4})\s+(.*)$/.exec(ln);
    if (h) {
      out.push(<Text key={i} style={[st.mdH, h[1].length === 1 && { fontSize: 22 }, h[1].length >= 3 && { fontSize: 15 }]}>{inline(h[2])}</Text>);
      return;
    }
    if (/^\s*\|?[\s:-]+\|[\s|:-]*$/.test(ln)) return; // table separator row
    if (ln.includes('|') && ln.trim().startsWith('|')) {
      const cells = ln.split('|').map((c) => c.trim()).filter(Boolean);
      out.push(<Text key={i} selectable style={[st.p, { fontSize: 13 }]}>{inline(cells.join('  |  '))}</Text>);
      return;
    }
    const b = /^(\s*)([-*]|\d+\.)\s+(.*)$/.exec(ln);
    if (b) {
      out.push(
        <View key={i} style={{ flexDirection: 'row', paddingLeft: Math.min(b[1].length, 8) * 4 }}>
          <Text style={[st.p, { width: 22, color: C.gold }]}>{/\d/.test(b[2]) ? b[2] : '•'}</Text>
          <Text selectable style={[st.p, { flex: 1 }]}>{inline(b[3])}</Text>
        </View>,
      );
      return;
    }
    if (!ln.trim()) { out.push(<View key={i} style={{ height: 6 }} />); return; }
    out.push(<Text key={i} selectable style={st.p}>{inline(ln)}</Text>);
  });
  if (code) out.push(<View key="end" style={st.code}><Text selectable style={st.codeText}>{(code as string[]).join('\n')}</Text></View>);
  return <View>{out}</View>;
}

function inline(s: string): React.ReactNode[] {
  return s.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**') && p.length > 4) return <Text key={i} style={{ fontWeight: '700', color: C.gold }}>{p.slice(2, -2)}</Text>;
    if (p.startsWith('`') && p.endsWith('`') && p.length > 2) return <Text key={i} style={{ fontFamily: 'Courier', color: C.gold }}>{p.slice(1, -1)}</Text>;
    return p;
  });
}

const st = StyleSheet.create({
  screen: { padding: S.lg, paddingTop: S.xl },
  title: { color: C.gold, fontSize: 24, fontWeight: '300', letterSpacing: 2, marginBottom: 4 },
  subtitle: { color: C.muted, fontSize: 13, marginBottom: S.lg, lineHeight: 18 },
  card: { backgroundColor: C.panel, borderColor: C.border, borderWidth: 1, borderRadius: 12, padding: S.lg, marginBottom: S.md },
  h: { color: C.text, fontSize: 16, fontWeight: '600', marginBottom: S.sm },
  p: { color: C.text, fontSize: 14, lineHeight: 21, marginBottom: 4 },
  label: { color: C.muted, fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.2, marginBottom: 6 },
  btn: { borderRadius: 10, paddingVertical: 13, paddingHorizontal: S.lg, alignItems: 'center', justifyContent: 'center' },
  btnText: { color: C.text, fontWeight: '600', fontSize: 15 },
  chip: { borderWidth: 1, borderColor: C.border, borderRadius: 18, paddingVertical: 7, paddingHorizontal: 12, marginRight: 6, marginBottom: 6 },
  chipText: { color: C.muted, fontSize: 13 },
  input: { backgroundColor: C.input, borderColor: C.border, borderWidth: 1, borderRadius: 10, color: C.text, padding: 12, fontSize: 15 },
  banner: { borderWidth: 1, borderRadius: 10, padding: S.md, marginBottom: S.md, backgroundColor: C.panel },
  mdH: { color: C.gold, fontSize: 18, fontWeight: '600', marginTop: S.md, marginBottom: 4 },
  code: { backgroundColor: C.input, borderRadius: 8, borderColor: C.border, borderWidth: 1, padding: S.md, marginVertical: 6 },
  codeText: { color: C.text, fontFamily: 'Courier', fontSize: 12, lineHeight: 17 },
});
