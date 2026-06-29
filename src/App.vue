<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { theme } from 'ant-design-vue'
import { useVisionLog } from './composables/useVisionLog'

// ─── Static config ──────────────────────────────────────────────────────────
const NODES = [
  { id: 3, freq: 174, label: 'NODE 3' },
  { id: 6, freq: 528, label: 'NODE 6' },
  { id: 9, freq: 963, label: 'NODE 9' },
]

const themeConfig = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#dfb76c',
    colorBgBase: '#0c0a0e',
    colorBgContainer: '#14121a',
    borderRadius: 12,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  },
}

// ─── UI state ───────────────────────────────────────────────────────────────
const { visions, load, add, remove } = useVisionLog()
const visionInput = ref('')
const centerLabel = ref('369')
const activeNode = ref(null)

// ─── Audio engine (Web Audio) ───────────────────────────────────────────────
const engine = reactive({ running: false })
let audioCtx = null
let primaryOsc = null
let spatialPanner = null
let panTimer = null
let targetFreq = 528

function spatialPanning() {
  if (!engine.running || !spatialPanner || !audioCtx) return
  const wave = Math.sin(Date.now() / (1000 * 1.618))
  spatialPanner.pan.setValueAtTime(wave, audioCtx.currentTime)
  panTimer = setTimeout(spatialPanning, 30)
}

function teardownAudio() {
  if (panTimer) {
    clearTimeout(panTimer)
    panTimer = null
  }
  if (primaryOsc) {
    try {
      primaryOsc.stop()
    } catch {
      /* already stopped */
    }
    primaryOsc.disconnect()
    primaryOsc = null
  }
  if (spatialPanner) {
    spatialPanner.disconnect()
    spatialPanner = null
  }
}

function stopEngine() {
  engine.running = false
  activeNode.value = null
  centerLabel.value = '369'
  teardownAudio()
  stopAnimation()
}

function toggleNode(node) {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)()
  }

  // Tapping the active node again powers the core down.
  if (engine.running && activeNode.value === node.id) {
    stopEngine()
    return
  }

  // Switching nodes: tear down the previous oscillator first.
  teardownAudio()

  engine.running = true
  activeNode.value = node.id
  targetFreq = node.freq
  centerLabel.value = String(node.id)

  const text = visionInput.value.trim() || 'Harmonic Matrix Meditation'
  add({ node: node.id, freq: node.freq, text })
  visionInput.value = ''

  primaryOsc = audioCtx.createOscillator()
  spatialPanner = audioCtx.createStereoPanner ? audioCtx.createStereoPanner() : null
  const localGain = audioCtx.createGain()

  primaryOsc.type = 'sine'
  primaryOsc.frequency.setValueAtTime(node.freq, audioCtx.currentTime)
  localGain.gain.setValueAtTime(0.12, audioCtx.currentTime)

  if (spatialPanner) {
    primaryOsc.connect(spatialPanner).connect(localGain)
  } else {
    primaryOsc.connect(localGain)
  }
  localGain.connect(audioCtx.destination)
  primaryOsc.start()

  spatialPanning()
  startAnimation()

  if ('vibrate' in navigator) navigator.vibrate(node.id * 30)
}

// ─── Canvas vortex ──────────────────────────────────────────────────────────
const canvasRef = ref(null)
let ctx = null
let rafId = null
let spatialRotation = 0

function resizeCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  canvas.width = canvas.offsetWidth
  canvas.height = canvas.offsetHeight
  if (!engine.running) draw()
}

function draw() {
  const canvas = canvasRef.value
  if (!canvas || !ctx) return
  const cx = canvas.width / 2
  const cy = canvas.height / 2

  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // Static golden-ratio guide circles.
  ctx.strokeStyle = '#1e1710'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.arc(cx, cy, 80, 0, Math.PI * 2)
  ctx.arc(cx, cy, 80 / 1.618, 0, Math.PI * 2)
  ctx.stroke()

  if (engine.running) {
    ctx.strokeStyle = activeNode.value === 9 ? '#ff4d4d' : 'rgba(212, 175, 55, 0.8)'
    ctx.lineWidth = 1.5
    ctx.beginPath()
    let radius = 3
    for (let i = 0; i < 200; i++) {
      const radAngle = i * (0.1 / 1.618) + spatialRotation
      const x = cx + Math.cos(radAngle) * radius
      const y = cy + Math.sin(radAngle) * radius
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
      radius += activeNode.value * 0.04
    }
    ctx.stroke()
  } else {
    // Idle crosshair.
    ctx.strokeStyle = '#2b2116'
    ctx.beginPath()
    ctx.moveTo(cx - 70, cy)
    ctx.lineTo(cx + 70, cy)
    ctx.moveTo(cx, cy - 70)
    ctx.lineTo(cx, cy + 70)
    ctx.stroke()
  }
}

function startAnimation() {
  if (rafId) cancelAnimationFrame(rafId)
  const loop = () => {
    draw()
    spatialRotation += targetFreq / 35000
    rafId = requestAnimationFrame(loop)
  }
  loop()
}

function stopAnimation() {
  if (rafId) {
    cancelAnimationFrame(rafId)
    rafId = null
  }
  draw()
}

// ─── Lifecycle ──────────────────────────────────────────────────────────────
onMounted(() => {
  ctx = canvasRef.value.getContext('2d')
  resizeCanvas()
  window.addEventListener('resize', resizeCanvas)
  load()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCanvas)
  stopEngine()
  if (audioCtx) {
    audioCtx.close?.()
    audioCtx = null
  }
})
</script>

<template>
  <a-config-provider :theme="themeConfig">
    <div class="hub-container">
      <header class="app-header">
        <h1>VITRUVIAN 369 CORE</h1>
        <div class="subtitle">Time Frequencies &amp; Spatial Dynamics</div>
      </header>

      <div class="layout-grid">
        <!-- Workbench -->
        <a-card class="panel" :body-style="{ display: 'flex', flexDirection: 'column' }">
          <div class="vessel-view">
            <canvas ref="canvasRef"></canvas>
            <div class="center-node-status">{{ centerLabel }}</div>
          </div>

          <a-textarea
            v-model:value="visionInput"
            :rows="3"
            class="vision-input"
            placeholder="Log your 369 pattern or script visual sequence here before striking a vector button..."
          />

          <div class="node-grid">
            <a-button
              v-for="node in NODES"
              :key="node.id"
              block
              size="large"
              class="node-btn"
              :type="activeNode === node.id ? 'primary' : 'default'"
              @click="toggleNode(node)"
            >
              {{ node.label }}
            </a-button>
          </div>
        </a-card>

        <!-- Vision log -->
        <a-card class="panel" title="Persistent Vision Log">
          <a-empty
            v-if="visions.length === 0"
            description="No current entries recorded. Log a vision map on the left workbench panel."
          />
          <a-list v-else class="project-list" :data-source="visions" item-layout="vertical">
            <template #renderItem="{ item }">
              <a-list-item class="project-card">
                <!-- {{ }} auto-escapes, so the original innerHTML XSS is gone. -->
                <div class="card-body">"{{ item.text }}"</div>
                <div class="card-footer">
                  <span>Vector {{ item.node }} ({{ item.freq }}Hz) · {{ item.timestamp }}</span>
                  <a-button type="link" danger size="small" @click="remove(item.uid)">
                    Clear
                  </a-button>
                </div>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </div>
    </div>
  </a-config-provider>
</template>

<style scoped>
.hub-container {
  width: 100%;
  max-width: 950px;
  padding: 20px;
  box-sizing: border-box;
}

.app-header {
  text-align: center;
  border-bottom: 1px solid #2b2533;
  padding-bottom: 15px;
  margin-bottom: 25px;
}

.app-header h1 {
  font-size: 1.6rem;
  margin: 0;
  font-weight: 300;
  letter-spacing: 4px;
  color: #dfb76c;
}

.subtitle {
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: #827b87;
  margin-top: 6px;
}

.layout-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 25px;
}

@media (min-width: 768px) {
  .layout-grid {
    grid-template-columns: 1.2fr 1fr;
  }
}

.panel {
  box-shadow: 0 15px 40px rgba(0, 0, 0, 0.6);
}

.vessel-view {
  width: 100%;
  height: 220px;
  background: #050403;
  border: 1px solid #2b2533;
  border-radius: 12px;
  margin-bottom: 20px;
  position: relative;
  box-shadow: inset 0 0 25px rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.vessel-view canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.center-node-status {
  font-size: 2.5rem;
  font-weight: 200;
  color: #dfb76c;
  z-index: 5;
  letter-spacing: 2px;
  opacity: 0.8;
}

.vision-input {
  margin-bottom: 15px;
}

.node-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.node-btn {
  font-weight: 600;
  letter-spacing: 1px;
  height: 56px;
}

.project-list {
  max-height: 480px;
  overflow-y: auto;
}

.project-card {
  border-left: 3px solid #dfb76c;
  padding-left: 14px;
}

.card-body {
  font-size: 0.9rem;
  line-height: 1.5;
  margin-bottom: 10px;
  white-space: pre-wrap;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  font-size: 0.75rem;
  color: #827b87;
}
</style>
