<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Vitruvian 369 Core</title>
    <style>
        :root {
            --bg-main: #0c0a0e;
            --panel-bg: #14121a;
            --accent-gold: #dfb76c;
            --accent-purple: #7045af;
            --text-light: #e6dfd5;
            --text-muted: #827b87;
            --border-color: #2b2533;
            --input-bg: #070609;
        }

        body {
            background-color: var(--bg-main);
            color: var(--text-light);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            min-height: 100vh;
            overflow-x: hidden;
            -webkit-user-select: none;
            user-select: none;
        }

        .hub-container {
            width: 100%;
            max-width: 950px;
            padding: 20px;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
        }

        header {
            text-align: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 15px;
            margin-bottom: 25px;
        }

        h1 {
            font-size: 1.6rem;
            margin: 0;
            font-weight: 300;
            letter-spacing: 4px;
            color: var(--accent-gold);
        }

        .subtitle {
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: var(--text-muted);
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
            background-color: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 20px;
            box-shadow: 0 15px 40px rgba(0,0,0,0.6);
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
        }

        .vessel-view {
            width: 100%;
            height: 220px;
            background: #050403;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            margin-bottom: 20px;
            position: relative;
            box-shadow: inset 0 0 25px rgba(0,0,0,0.9);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        canvas {
            width: 100%;
            height: 100%;
            position: absolute;
            top: 0;
            left: 0;
        }

        .center-node-status {
            font-size: 2.5rem;
            font-weight: 200;
            color: var(--accent-gold);
            z-index: 5;
            letter-spacing: 2px;
            opacity: 0.8;
        }

        textarea {
            width: 100%;
            height: 70px;
            background: var(--input-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: #fff;
            padding: 12px;
            font-family: inherit;
            font-size: 0.95rem;
            resize: none;
            box-sizing: border-box;
            margin-bottom: 15px;
        }

        textarea:focus {
            outline: none;
            border-color: var(--accent-gold);
        }

        .node-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
        }

        .node-btn {
            background: #17130e;
            border: 1px solid var(--border-color);
            color: var(--text-light);
            padding: 18px 5px;
            border-radius: 12px;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s ease;
            font-weight: 600;
            letter-spacing: 1px;
        }

        .node-btn.active {
            background: var(--accent-gold);
            color: var(--bg-main);
            border-color: var(--accent-gold);
            box-shadow: 0 0 20px rgba(223, 183, 108, 0.4);
        }

        .project-list {
            display: flex;
            flex-direction: column;
            gap: 15px;
            max-height: 480px;
            overflow-y: auto;
        }

        .project-card {
            background: var(--input-bg);
            border-left: 3px solid var(--accent-gold);
            border-top: 1px solid var(--border-color);
            border-right: 1px solid var(--border-color);
            border-bottom: 1px solid var(--border-color);
            border-radius: 0 10px 10px 0;
            padding: 15px;
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
            font-size: 0.75rem;
            color: var(--text-muted);
            border-top: 1px dashed rgba(255,255,255,0.05);
            padding-top: 8px;
        }

        .btn-delete {
            background: transparent;
            border: none;
            color: #ff5555;
            cursor: pointer;
        }

        .empty-state {
            text-align: center;
            color: var(--text-muted);
            font-style: italic;
            padding: 40px 0;
        }
    </style>
</head>
<body>

    <div class="hub-container">
        <header>
            <h1>VITRUVIAN 369 CORE</h1>
            <div class="subtitle">Time Frequencies & Spatial Dynamics</div>
        </header>

        <div class="layout-grid">
            <div class="panel">
                <div class="vessel-view">
                    <canvas id="geometryCanvas"></canvas>
                    <div class="center-node-status" id="centerLabel">369</div>
                </div>

                <textarea id="visionInput" placeholder="Log your 369 pattern or script visual sequence here before striking a vector button..."></textarea>

                <div class="node-grid">
                    <button class="node-btn" id="n3" onclick="toggleEngineCore(3, 174)">NODE 3</button>
                    <button class="node-btn" id="n6" onclick="toggleEngineCore(6, 528)">NODE 6</button>
                    <button class="node-btn" id="n9" onclick="toggleEngineCore(9, 963)">NODE 9</button>
                </div>
            </div>

            <div class="panel">
                <div style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 15px; color: var(--accent-gold);">Persistent Vision Log</div>
                <div class="project-list" id="feedDisplay"></div>
            </div>
        </div>
    </div>

    <script>
        let audioCtx = null;
        let primaryOsc = null;
        let spatialPanner = null;
        let isEngineRunning = false;
        let activeNodeIndex = null;
        let targetFreq = 528;

        const canvas = document.getElementById('geometryCanvas');
        const ctx = canvas.getContext('2d');
        let spatialRotation = 0;
        let storedVisions = [];

        window.onload = function() {
            initAppCanvas();
            loadMemoryCache();
        };

        function initAppCanvas() {
            canvas.width = canvas.offsetWidth;
            canvas.height = canvas.offsetHeight;
            renderVortexGraphics();
        }

        function renderVortexGraphics() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            const cx = canvas.width / 2;
            const cy = canvas.height / 2;

            ctx.strokeStyle = '#1e1710';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.arc(cx, cy, 80, 0, Math.PI * 2);
            ctx.arc(cx, cy, 80 / 1.618, 0, Math.PI * 2);
            ctx.stroke();

            if (isEngineRunning) {
                ctx.strokeStyle = activeNodeIndex === 9 ? '#ff4d4d' : 'rgba(212, 175, 55, 0.8)';
                ctx.lineWidth = 1.5;
                ctx.beginPath();

                let radius = 3;
                for (let i = 0; i < 200; i++) {
                    let radAngle = i * (0.1 / 1.618) + spatialRotation;
                    let x = cx + Math.cos(radAngle) * radius;
                    let y = cy + Math.sin(radAngle) * radius;

                    if (i === 0) ctx.moveTo(x, y);
                    else ctx.lineTo(x, y);

                    radius += (activeNodeIndex * 0.04);
                }
                ctx.stroke();
                spatialRotation += (targetFreq / 35000);
                requestAnimationFrame(renderVortexGraphics);
            } else {
                ctx.strokeStyle = '#2b2116';
                ctx.beginPath();
                ctx.moveTo(cx - 70, cy); ctx.lineTo(cx + 70, cy);
                ctx.moveTo(cx, cy - 70); ctx.lineTo(cx, cy + 70);
                ctx.stroke();
            }
        }

        function toggleEngineCore(nodeNum, frequency) {
            if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const inputField = document.getElementById('visionInput');
            const centerLabel = document.getElementById('centerLabel');

            if (isEngineRunning && activeNodeIndex === nodeNum) {
                killEngineCore();
                return;
            }

            if (primaryOsc) { try { primaryOsc.stop(); } catch(e){} }

            isEngineRunning = true;
            activeNodeIndex = nodeNum;
            targetFreq = frequency;
            centerLabel.innerText = nodeNum;

            document.querySelectorAll('.node-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById(`n${nodeNum}`).classList.add('active');

            const visionText = inputField.value.trim();
            saveVisionItem(nodeNum, frequency, visionText || "Harmonic Matrix Meditation");
            inputField.value = ""; 

            primaryOsc = audioCtx.createOscillator();
            spatialPanner = audioCtx.createStereoPanner ? audioCtx.createStereoPanner() : null;
            const localGain = audioCtx.createGain();

            primaryOsc.type = 'sine';
            primaryOsc.frequency.setValueAtTime(frequency, audioCtx.currentTime);
            localGain.gain.setValueAtTime(0.12, audioCtx.currentTime);

            if (spatialPanner) {
                primaryOsc.connect(spatialPanner).connect(localGain);
            } else {
                primaryOsc.connect(localGain);
            }
            localGain.connect(audioCtx.destination);
            primaryOsc.start();

            executeSpatialPanning();
            renderVortexGraphics();

            if ("vibrate" in navigator) navigator.vibrate(nodeNum * 30);
        }

        function executeSpatialPanning() {
            if (!isEngineRunning || !spatialPanner) return;
            let spatialWave = Math.sin(Date.now() / (1000 * 1.618));
            spatialPanner.pan.setValueAtTime(spatialWave, audioCtx.currentTime);
            setTimeout(executeSpatialPanning, 30);
        }

        function killEngineCore() {
            isEngineRunning = false;
            activeNodeIndex = null;
            document.getElementById('centerLabel').innerText = "369";
            if (primaryOsc) { try { primaryOsc.stop(); } catch(e){} }
            document.querySelectorAll('.node-btn').forEach(btn => btn.classList.remove('active'));
            renderVortexGraphics();
        }

        function saveVisionItem(node, freq, text) {
            const timestamp = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            storedVisions.unshift({ node, freq, text, timestamp, uid: Date.now() }); 
            localStorage.setItem('core_vision_data', JSON.stringify(storedVisions));
            renderFeedInterface();
        }

        function loadMemoryCache() {
            const cache = localStorage.getItem('core_vision_data');
            if (cache) storedVisions = JSON.parse(cache);
            renderFeedInterface();
        }

        function clearRecord(uid) {
            storedVisions = storedVisions.filter(item => item.uid !== uid);
            localStorage.setItem('core_vision_data', JSON.stringify(storedVisions));
            renderFeedInterface();
        }

        function renderFeedInterface() {
            const listFeed = document.getElementById('feedDisplay');
            if (storedVisions.length === 0) {
                listFeed.innerHTML = `<div class="empty-state">No current entries recorded. Log a vision map on the left workbench panel.</div>`;
                return;
            }
            listFeed.innerHTML = storedVisions.map(item => `
                <div class="project-card">
                    <div class="card-body">"${item.text}"</div>
                    <div class="card-footer">
                        <div>Vector ${item.node} (${item.freq}Hz) | ${item.timestamp}</div>
                        <button class="btn-delete" onclick="clearRecord(${item.uid})">Clear</button>
                    </div>
                </div>
            `).join('');
        }
    </script>
</body>
</html>