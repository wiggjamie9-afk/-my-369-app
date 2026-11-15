import React, { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { StoreProvider, useStore } from './src/store';
import { C } from './src/theme';
import LearnScreen from './src/screens/LearnScreen';
import BlueprintScreen from './src/screens/BlueprintScreen';
import ResearchScreen from './src/screens/ResearchScreen';
import IdeasScreen from './src/screens/IdeasScreen';
import SettingsScreen from './src/screens/SettingsScreen';

type Tab = 'learn' | 'team' | 'research' | 'ideas' | 'settings';
const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'learn', label: 'Learn', icon: '📘' },
  { id: 'team', label: 'Team', icon: '🧩' },
  { id: 'research', label: 'Research', icon: '🔎' },
  { id: 'ideas', label: 'Ideas', icon: '💡' },
  { id: 'settings', label: 'Settings', icon: '⚙️' },
];

function Shell() {
  const { ready } = useStore();
  const [tab, setTab] = useState<Tab>('research');
  if (!ready) return <View style={styles.center}><ActivityIndicator color={C.gold} /></View>;
  return (
    <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
      <View style={{ flex: 1, width: '100%', maxWidth: 720, alignSelf: 'center' }}>
        {tab === 'learn' && <LearnScreen />}
        {tab === 'team' && <BlueprintScreen goSettings={() => setTab('settings')} />}
        {tab === 'research' && <ResearchScreen goSettings={() => setTab('settings')} />}
        {tab === 'ideas' && <IdeasScreen />}
        {tab === 'settings' && <SettingsScreen />}
      </View>
      <View style={styles.bar}>
        {TABS.map((t) => (
          <Pressable key={t.id} style={styles.tab} onPress={() => setTab(t.id)} accessibilityRole="button" accessibilityLabel={t.label}>
            <Text style={{ fontSize: 20, opacity: tab === t.id ? 1 : 0.5 }}>{t.icon}</Text>
            <Text style={[styles.tabText, tab === t.id && { color: C.gold }]}>{t.label}</Text>
          </Pressable>
        ))}
      </View>
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <StoreProvider>
        <StatusBar style="light" />
        <Shell />
      </StoreProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  center: { flex: 1, backgroundColor: C.bg, alignItems: 'center', justifyContent: 'center' },
  bar: { flexDirection: 'row', borderTopWidth: 1, borderTopColor: C.border, backgroundColor: C.panel },
  tab: { flex: 1, alignItems: 'center', paddingVertical: 8 },
  tabText: { color: C.muted, fontSize: 11, marginTop: 2 },
});
