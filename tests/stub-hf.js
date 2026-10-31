window.__calls = [];
let judgeN = 0;
const scores = (globalThis.__scores = globalThis.__scores || [5, 6, 4, 3, 9, 7, 6, 5, 9, 8, 9, 9, 9, 9, 9, 9, 9, 9]);
async function img(color){ const c=new OffscreenCanvas(320,180); const x=c.getContext('2d'); x.fillStyle=color; x.fillRect(0,0,320,180); return c.convertToBlob({type:'image/png'}); }
async function vid(color){
  const c=document.createElement('canvas'); c.width=320; c.height=180; const x=c.getContext('2d');
  const rec=new MediaRecorder(c.captureStream(30),{mimeType:'video/webm'}); const parts=[]; rec.ondataavailable=e=>parts.push(e.data);
  rec.start(); const t0=performance.now();
  await new Promise(r=>{ (function f(){ const p=(performance.now()-t0)/600; x.fillStyle=color; x.fillRect(0,0,320,180); x.fillStyle='#fff'; x.fillRect(p*300,80,20,20); if(p<1) requestAnimationFrame(f); else r(); })(); });
  rec.stop(); await new Promise(r=>rec.onstop=r); return new Blob(parts,{type:'video/webm'});
}
const colors=['#dfb76c','#7045af','#3a8','#a53'];
export class InferenceClient {
  constructor(t){ this.t=t; }
  async textToImage(a,o){ window.__calls.push(['t2i',a.model,a.inputs.slice(0,40)]); await new Promise(r=>setTimeout(r,50+Math.random()*100)); if(window.__failModel===a.model) throw new Error('No provider available for model'); return img(colors[Math.floor(Math.random()*4)]); }
  async imageToImage(a,o){ window.__calls.push(['i2i',a.model]); return img('#555'); }
  async textToVideo(a,o){ window.__calls.push(['t2v',a.model]); return vid(colors[Math.floor(Math.random()*4)]); }
  async imageToVideo(a,o){ window.__calls.push(['i2v',a.model, a.inputs instanceof Blob]); return vid('#246'); }
  async chatCompletion(a,o){
    if(window.__judgeDown) throw new Error('500 judge down');
    const c=a.messages[0].content;
    if(typeof c==='string'){ window.__calls.push(['director']); window.__lastDirector=c; return {choices:[{message:{content:'"An expanded cinematic prompt about a golden spiral"'}}]}; }
    const imgs=c.filter(p=>p.type==='image_url').length; window.__lastJudge=c[0].text; const s=scores[judgeN++ % scores.length];
    window.__calls.push(['judge',imgs,s]);
    return {choices:[{message:{content:'Sure! {"score": '+s+', "issues": ["<b>wrong</b> lighting"], "improved_prompt": "improved prompt v'+judgeN+'"}'}}]};
  }
}
