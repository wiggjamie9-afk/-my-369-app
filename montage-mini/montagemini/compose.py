"""Stage 4 — composition.

Renders the planned production into a single self-contained HTML file that
plays in any browser: a canvas animates each scene's synthesized background
(gradient + motif + Ken Burns camera), kinetic headlines fade through, and
word-level captions highlight in sync. Optional narration uses the browser's
built-in SpeechSynthesis (offline, no key). This is montage-mini's stand-in
for Remotion/FFmpeg — the deliverable is a playable HTML "video".
"""

from __future__ import annotations

import json
from typing import List

from .sceneplan import Scene
from .styles import get_playbook


def build_production(brief, script, scenes: List[Scene], visuals: List[dict]) -> dict:
    pb = get_playbook(brief.tone)
    scene_dicts = []
    for s, v in zip(scenes, visuals):
        scene_dicts.append(
            {
                "index": s.index,
                "headline": s.headline,
                "narration": s.narration,
                "start": s.start,
                "duration": s.duration,
                "words": [{"text": w.text, "start": w.start, "end": w.end} for w in s.words],
                "visual": v,
            }
        )
    total = round(scenes[-1].start + scenes[-1].duration, 3) if scenes else 0.0
    return {
        "title": script.title,
        "tone": brief.tone,
        "backend": script.backend,
        "width": brief.width,
        "height": brief.height,
        "aspect": brief.aspect,
        "profile": brief.profile,
        "font": pb["font"],
        "text": pb["text"],
        "muted": pb["muted"],
        "accent": pb["accent"],
        "vignette": pb["vignette"],
        "narration": brief.narration,
        "total": total,
        "scenes": scene_dicts,
    }


def render_html(production: dict) -> str:
    payload = json.dumps(production, ensure_ascii=False)
    return _TEMPLATE.replace("/*__PRODUCTION__*/", payload)


# --------------------------------------------------------------------------- #
# The player. Pure HTML/CSS/JS, no external resources.
# --------------------------------------------------------------------------- #

_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>montage-mini</title>
<style>
  :root { --ui: #cfd9e6; }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: #060709; color: var(--ui);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    min-height: 100vh; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 14px; padding: 18px;
  }
  #stageWrap { width: min(96vw, 1100px); }
  #stage {
    position: relative; width: 100%; border-radius: 12px; overflow: hidden;
    background: #000; box-shadow: 0 20px 60px rgba(0,0,0,.6);
  }
  #canvas { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
  #overlay { position: absolute; inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center; pointer-events: none; }
  #headline {
    font-weight: 700; letter-spacing: 3px; text-align: center;
    padding: 0 8%; line-height: 1.1; opacity: 0; transition: none;
  }
  #captions {
    position: absolute; bottom: 9%; left: 0; right: 0; text-align: center;
    padding: 0 8%; font-weight: 600; line-height: 1.4;
  }
  #captions .w { opacity: .45; transition: opacity .12s, color .12s; }
  #captions .w.on { opacity: 1; }
  #vignette { position: absolute; inset: 0; pointer-events: none;
    background: radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,.85) 100%); }
  #grain { position: absolute; inset: 0; pointer-events: none; opacity: .05;
    mix-blend-mode: overlay;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    background-size: 180px 180px; }
  #controls {
    width: min(96vw, 1100px); display: flex; align-items: center; gap: 12px;
    background: #11151c; border: 1px solid #1e2632; border-radius: 10px; padding: 10px 14px;
  }
  button {
    background: #1b222e; color: var(--ui); border: 1px solid #2a3442;
    border-radius: 7px; padding: 8px 12px; cursor: pointer; font-size: 13px;
  }
  button:hover { background: #232c3a; }
  button.active { background: #2c5cff; border-color: #2c5cff; color: #fff; }
  #scrub { flex: 1; appearance: none; height: 5px; border-radius: 3px;
    background: #2a3442; outline: none; cursor: pointer; }
  #scrub::-webkit-slider-thumb { appearance: none; width: 14px; height: 14px;
    border-radius: 50%; background: #2c5cff; cursor: pointer; }
  #time { font-variant-numeric: tabular-nums; font-size: 13px; color: #8aa0bd; min-width: 86px; text-align: right; }
  #meta { width: min(96vw,1100px); font-size: 12px; color: #6b7a8d; display: flex;
    justify-content: space-between; flex-wrap: wrap; gap: 8px; }
  #meta b { color: #8aa0bd; font-weight: 600; }
</style>
</head>
<body>
  <div id="meta">
    <span id="metaTitle"></span>
    <span id="metaSpecs"></span>
  </div>
  <div id="stageWrap">
    <div id="stage">
      <canvas id="canvas"></canvas>
      <div id="overlay"><div id="headline"></div></div>
      <div id="captions"></div>
      <div id="vignette"></div>
      <div id="grain"></div>
    </div>
  </div>
  <div id="controls">
    <button id="playBtn">▶ Play</button>
    <button id="restartBtn">⟲</button>
    <input id="scrub" type="range" min="0" max="1000" value="0">
    <span id="time">0:00 / 0:00</span>
    <button id="voiceBtn" class="active">🔊 Voice</button>
  </div>

<script>
const P = /*__PRODUCTION__*/;

// ---- setup -------------------------------------------------------------
const stageWrap = document.getElementById('stageWrap');
const stage = document.getElementById('stage');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const headlineEl = document.getElementById('headline');
const captionsEl = document.getElementById('captions');
const vignetteEl = document.getElementById('vignette');
const playBtn = document.getElementById('playBtn');
const restartBtn = document.getElementById('restartBtn');
const voiceBtn = document.getElementById('voiceBtn');
const scrub = document.getElementById('scrub');
const timeEl = document.getElementById('time');

headlineEl.style.fontFamily = P.font;
headlineEl.style.color = P.text;
headlineEl.style.textShadow = '0 2px 24px rgba(0,0,0,.75), 0 0 60px ' + P.accent + '55';
captionsEl.style.fontFamily = P.font;
captionsEl.style.color = P.text;
captionsEl.style.textShadow = '0 2px 12px rgba(0,0,0,.85)';
vignetteEl.style.opacity = P.vignette;
document.getElementById('metaTitle').innerHTML =
  '<b>' + escapeHtml(P.title) + '</b> · ' + P.scenes.length + ' scenes · script: ' + P.backend;
document.getElementById('metaSpecs').textContent =
  P.profile + ' · ' + P.aspect + ' · ' + P.total.toFixed(1) + 's';

let DPR = Math.min(window.devicePixelRatio || 1, 2);
function fit() {
  const w = stageWrap.clientWidth || stage.getBoundingClientRect().width;
  stage.style.height = Math.round(w * P.height / P.width) + 'px';
  const r = stage.getBoundingClientRect();
  canvas.width = Math.max(1, Math.round(r.width * DPR));
  canvas.height = Math.max(1, Math.round(r.height * DPR));
  const base = Math.min(r.width, r.height);
  headlineEl.style.fontSize = (base * 0.075) + 'px';
  captionsEl.style.fontSize = (base * 0.040) + 'px';
}
window.addEventListener('resize', fit);
fit();

// ---- playback state ----------------------------------------------------
let t = 0;              // current time in seconds
let playing = false;
let last = 0;
let voiceOn = ('speechSynthesis' in window) && P.narration;
let spokenScene = -1;
if (!('speechSynthesis' in window) || !P.narration) { voiceBtn.style.display = 'none'; }

function sceneAt(time) {
  for (let i = P.scenes.length - 1; i >= 0; i--) {
    if (time >= P.scenes[i].start) return P.scenes[i];
  }
  return P.scenes[0];
}

// ---- background rendering ---------------------------------------------
function rand(seed) { // deterministic pseudo-random in [0,1)
  let x = Math.sin(seed * 12.9898) * 43758.5453;
  return x - Math.floor(x);
}

function drawScene(scene, p) {
  const v = scene.visual;
  const W = canvas.width, H = canvas.height;
  ctx.save();
  ctx.clearRect(0, 0, W, H);

  // Ken Burns camera: scale + pan over scene-local progress p (0..1).
  const zoom = 1.05 + 0.10 * p * v.zoom_dir + (v.zoom_dir < 0 ? 0.10 : 0);
  const tx = v.pan_x * W * 0.08 * p;
  const ty = v.pan_y * H * 0.08 * p;
  ctx.translate(W/2 + tx, H/2 + ty);
  ctx.scale(zoom, zoom);
  ctx.translate(-W/2, -H/2);

  // Gradient base.
  const g = ctx.createLinearGradient(0, 0, W, H);
  g.addColorStop(0, v.bg0);
  g.addColorStop(1, v.bg1);
  ctx.fillStyle = g;
  ctx.fillRect(-W*0.2, -H*0.2, W*1.4, H*1.4);

  drawMotif(v, W, H, p);
  ctx.restore();
}

function drawMotif(v, W, H, p) {
  const unit = Math.min(W, H);
  ctx.lineWidth = Math.max(1, unit * 0.0025);
  if (v.motif === 'grid') {
    ctx.strokeStyle = hexA(v.accent, 0.10);
    const step = unit * 0.10;
    for (let x = (p*step) % step; x < W; x += step) line(x,0,x,H);
    for (let y = (p*step) % step; y < H; y += step) line(0,y,W,y);
  } else if (v.motif === 'rays') {
    ctx.strokeStyle = hexA(v.accent, 0.12);
    const cx = W*0.5, cy = H*0.5, R = Math.hypot(W,H);
    for (let i=0;i<14;i++){
      const a = (i/14)*Math.PI*2 + p*0.4 + v.angle*0.0175;
      line(cx, cy, cx+Math.cos(a)*R, cy+Math.sin(a)*R);
    }
  } else if (v.motif === 'burst') {
    ctx.strokeStyle = hexA(v.accent2, 0.16);
    const cx=W*0.5, cy=H*0.5;
    for (let i=0;i<24;i++){
      const a=(i/24)*Math.PI*2;
      const r0=unit*0.05, r1=unit*(0.18+0.10*p);
      line(cx+Math.cos(a)*r0, cy+Math.sin(a)*r0, cx+Math.cos(a)*r1, cy+Math.sin(a)*r1);
    }
  } else if (v.motif === 'waves') {
    ctx.strokeStyle = hexA(v.accent, 0.14);
    for (let k=0;k<5;k++){
      ctx.beginPath();
      const yBase = H*(0.25+0.13*k);
      for (let x=0;x<=W;x+=unit*0.02){
        const y = yBase + Math.sin(x*0.006 + p*6 + k)*unit*0.03;
        x===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
      }
      ctx.stroke();
    }
  } else if (v.motif === 'cosmos') {
    const cx = W*0.5, cy = H*0.5, R = Math.max(W,H);
    // Drifting nebula clouds (soft radial color fields).
    const neb = ctx.globalCompositeOperation;
    ctx.globalCompositeOperation = 'lighter';
    for (let i=0;i<3;i++){
      const a = v.angle*0.0175 + i*2.1 + t*0.015;
      const nx = cx + Math.cos(a)*W*0.22, ny = cy + Math.sin(a*0.7)*H*0.22;
      const rad = R*(0.34+0.07*i);
      const col = (i % 2) ? v.accent : v.accent2;
      const rg = ctx.createRadialGradient(nx,ny,0,nx,ny,rad);
      rg.addColorStop(0, hexA(col, 0.12));
      rg.addColorStop(0.5, hexA(col, 0.05));
      rg.addColorStop(1, hexA(col, 0));
      ctx.fillStyle = rg; ctx.fillRect(0,0,W,H);
    }
    ctx.globalCompositeOperation = neb;
    // Parallax starfield: 3 depth layers drift at different speeds + twinkle.
    const layers = [[140,0.006,0.55],[90,0.013,0.9],[45,0.026,1.35]];
    let li = 0;
    for (const layer of layers){
      const count = layer[0], speed = layer[1], size = layer[2];
      for (let i=0;i<count;i++){
        const sd = v.seed + li*1009 + i*7;
        const sx = (rand(sd)*W + t*speed*W*0.35) % W;
        const sy = (rand(sd*3.1)*H + t*speed*H*0.12) % H;
        const tw = 0.35 + 0.65*Math.abs(Math.sin(t*1.6 + rand(sd*5.7)*6.283));
        const r = size * Math.min(W,H) * 0.0016 * (0.6 + rand(sd*9.3));
        ctx.fillStyle = hexA('#ffffff', 0.55*tw);
        ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI*2); ctx.fill();
      }
      li++;
    }
    // Central glow / distant sun.
    const gg = ctx.createRadialGradient(cx,cy,0,cx,cy,R*0.42);
    gg.addColorStop(0, hexA(v.accent, 0.14));
    gg.addColorStop(1, hexA(v.accent, 0));
    ctx.fillStyle = gg; ctx.fillRect(0,0,W,H);
  } else if (v.motif === 'embers') {
    for (let i=0;i<40;i++){
      const sx = rand(v.seed+i)*W;
      const baseY = rand(v.seed+i*7)*H;
      const speed = 0.3 + rand(v.seed+i*3)*0.7;
      const y = (baseY - p*H*speed + H) % H;
      const r = unit*0.004*(0.5+rand(v.seed+i*5));
      ctx.fillStyle = hexA(v.accent2, 0.5*rand(v.seed+i*11)+0.1);
      ctx.beginPath(); ctx.arc(sx, y, r, 0, Math.PI*2); ctx.fill();
    }
  }
}

function line(a,b,c,d){ ctx.beginPath(); ctx.moveTo(a,b); ctx.lineTo(c,d); ctx.stroke(); }
function hexA(hex, a){
  hex = hex.replace('#','');
  const r=parseInt(hex.slice(0,2),16), g=parseInt(hex.slice(2,4),16), b=parseInt(hex.slice(4,6),16);
  return 'rgba('+r+','+g+','+b+','+a+')';
}
function escapeHtml(s){ return s.replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

// ---- text + captions ---------------------------------------------------
let renderedScene = -1;
function renderText(scene, local) {
  if (scene.index !== renderedScene) {
    renderedScene = scene.index;
    headlineEl.textContent = scene.headline;
    captionsEl.innerHTML = scene.words.map((w,i) =>
      '<span class="w" data-i="'+i+'">'+escapeHtml(w.text)+'</span>').join(' ');
  }
  // Headline: fade in, hold, fade out within the scene.
  const d = scene.duration;
  let op = 1;
  if (local < 0.6) op = local/0.6;
  else if (local > d-0.6) op = Math.max(0, (d-local)/0.6);
  headlineEl.style.opacity = op.toFixed(3);

  // Word highlight.
  const spans = captionsEl.children;
  for (let i=0;i<scene.words.length;i++){
    const w = scene.words[i];
    const on = local >= w.start && local <= w.end + 0.05;
    const el = spans[i];
    if (!el) continue;
    if (on) { el.classList.add('on'); el.style.color = P.accent; }
    else { el.classList.remove('on'); el.style.color = ''; }
  }
}

// ---- narration ---------------------------------------------------------
function speak(scene) {
  if (!voiceOn) return;
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(scene.narration);
    u.rate = 0.98; u.pitch = 1.0;
    window.speechSynthesis.speak(u);
  } catch (e) {}
}
function stopVoice(){ try { window.speechSynthesis.cancel(); } catch(e){} }

// ---- loop --------------------------------------------------------------
function frame(now) {
  if (playing) {
    const dt = (now - last) / 1000;
    t += dt;
    if (t >= P.total) { t = P.total; pause(); }
  }
  last = now;

  const scene = sceneAt(t);
  const local = t - scene.start;
  drawScene(scene, Math.min(1, local / scene.duration));
  renderText(scene, local);

  if (playing && scene.index !== spokenScene) {
    spokenScene = scene.index;
    speak(scene);
  }

  scrub.value = Math.round((t / P.total) * 1000);
  timeEl.textContent = fmt(t) + ' / ' + fmt(P.total);
  requestAnimationFrame(frame);
}
function fmt(s){ const m=Math.floor(s/60), ss=Math.floor(s%60); return m+':'+String(ss).padStart(2,'0'); }

// ---- controls ----------------------------------------------------------
function play(){ if (t>=P.total) t=0; playing=true; playBtn.textContent='❚❚ Pause'; spokenScene=-1; }
function pause(){ playing=false; playBtn.textContent='▶ Play'; stopVoice(); }
playBtn.onclick = () => playing ? pause() : play();
restartBtn.onclick = () => { t=0; spokenScene=-1; renderedScene=-1; if(!playing) { } };
scrub.oninput = () => { t = (scrub.value/1000)*P.total; spokenScene=-1; stopVoice(); };
voiceBtn.onclick = () => {
  voiceOn = !voiceOn;
  voiceBtn.classList.toggle('active', voiceOn);
  if (!voiceOn) stopVoice(); else { spokenScene=-1; }
};

requestAnimationFrame(frame);
</script>
</body>
</html>
"""
