import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import { DEFAULT_MODEL, ModelId } from './data/models';
import { Blueprint, IdeaStatus, Report } from './types';

const STATE_KEY = 'lab369:state:v1';
const KEY_NAME = 'lab369_anthropic_key';

type Persisted = {
  model: ModelId;
  progress: Record<string, boolean>;
  reports: Report[];
  blueprints: Blueprint[];
};

const EMPTY: Persisted = { model: DEFAULT_MODEL, progress: {}, reports: [], blueprints: [] };

type Store = Persisted & {
  ready: boolean;
  apiKey: string;
  setApiKey: (k: string) => Promise<void>;
  setModel: (m: ModelId) => void;
  toggleStep: (id: string) => void;
  addReport: (r: Report) => void;
  addBlueprint: (b: Blueprint) => void;
  updateIdea: (reportId: string, ideaId: string, patch: { status?: IdeaStatus; notes?: string }) => void;
  deleteReport: (id: string) => void;
  exportAll: () => string;
  clearAll: () => Promise<void>;
};

const Ctx = createContext<Store | null>(null);

// SecureStore (Keychain / Keystore) on device; plain AsyncStorage on web preview only.
async function readKey(): Promise<string> {
  try {
    if (Platform.OS === 'web') return (await AsyncStorage.getItem(KEY_NAME)) ?? '';
    return (await SecureStore.getItemAsync(KEY_NAME)) ?? '';
  } catch {
    return '';
  }
}
async function writeKey(k: string) {
  if (Platform.OS === 'web') {
    if (k) await AsyncStorage.setItem(KEY_NAME, k);
    else await AsyncStorage.removeItem(KEY_NAME);
    return;
  }
  if (k) await SecureStore.setItemAsync(KEY_NAME, k);
  else await SecureStore.deleteItemAsync(KEY_NAME);
}

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<Persisted>(EMPTY);
  const [apiKey, setApiKeyState] = useState('');
  const [ready, setReady] = useState(false);
  const loaded = useRef(false);

  useEffect(() => {
    (async () => {
      try {
        const raw = await AsyncStorage.getItem(STATE_KEY);
        if (raw) setState({ ...EMPTY, ...JSON.parse(raw) });
      } catch {
        /* start fresh if storage is unreadable */
      }
      setApiKeyState(await readKey());
      loaded.current = true;
      setReady(true);
    })();
  }, []);

  useEffect(() => {
    if (!loaded.current) return;
    AsyncStorage.setItem(STATE_KEY, JSON.stringify(state)).catch(() => {});
  }, [state]);

  const setApiKey = useCallback(async (k: string) => {
    const v = k.trim();
    await writeKey(v);
    setApiKeyState(v);
  }, []);

  const value = useMemo<Store>(
    () => ({
      ...state,
      ready,
      apiKey,
      setApiKey,
      setModel: (model) => setState((s) => ({ ...s, model })),
      toggleStep: (id) => setState((s) => ({ ...s, progress: { ...s.progress, [id]: !s.progress[id] } })),
      addReport: (r) => setState((s) => ({ ...s, reports: [r, ...s.reports] })),
      addBlueprint: (b) => setState((s) => ({ ...s, blueprints: [b, ...s.blueprints] })),
      updateIdea: (reportId, ideaId, patch) =>
        setState((s) => ({
          ...s,
          reports: s.reports.map((r) =>
            r.id !== reportId ? r : { ...r, ideas: r.ideas.map((i) => (i.id === ideaId ? { ...i, ...patch } : i)) },
          ),
        })),
      deleteReport: (id) => setState((s) => ({ ...s, reports: s.reports.filter((r) => r.id !== id) })),
      exportAll: () => JSON.stringify(state, null, 2),
      clearAll: async () => {
        setState(EMPTY);
        await AsyncStorage.removeItem(STATE_KEY);
      },
    }),
    [state, ready, apiKey, setApiKey],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useStore(): Store {
  const v = useContext(Ctx);
  if (!v) throw new Error('useStore outside StoreProvider');
  return v;
}

export const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
