import { ref } from 'vue'

const STORAGE_KEY = 'core_vision_data'

/**
 * Reactive, localStorage-backed log of "vision" entries.
 * Mirrors the original app's persistence, but isolated and testable.
 */
export function useVisionLog() {
  const visions = ref([])

  function load() {
    try {
      const cache = localStorage.getItem(STORAGE_KEY)
      visions.value = cache ? JSON.parse(cache) : []
    } catch {
      // Corrupt / unavailable storage — start clean rather than crash.
      visions.value = []
    }
  }

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(visions.value))
    } catch {
      /* storage may be full or blocked; ignore */
    }
  }

  function add({ node, freq, text }) {
    const timestamp = new Date().toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    })
    visions.value.unshift({ node, freq, text, timestamp, uid: Date.now() })
    persist()
  }

  function remove(uid) {
    visions.value = visions.value.filter((item) => item.uid !== uid)
    persist()
  }

  return { visions, load, add, remove }
}
