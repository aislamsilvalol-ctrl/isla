"""ISLA web UI — one self-contained page, zero external assets.

Identity (V2 item 38): neutral near-black, system mono, ONE accent (amber =
attention/signal). No cards-inside-cards, no glow, no template look. Density
toggle FOCUS/DENSE, Cmd+K palette, SSE-driven — the screen reacts when the
world moves.
"""

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ISLA</title>
<style>
:root{--bg:#0B0C0D;--panel:#111314;--line:#232628;--ink:#E8EAE6;--mut:#8B9491;
      --dim:#565E5B;--sig:#FFAD33;--sig-dim:rgba(255,173,51,.12)}
*{box-sizing:border-box;margin:0}
body{background:var(--bg);color:var(--ink);
     font:13px/1.5 ui-monospace,'SF Mono',Menlo,Consolas,monospace}
a{color:var(--sig);text-decoration:none}
header{display:flex;align-items:center;gap:14px;padding:10px 16px;
       border-bottom:1px solid var(--line);position:sticky;top:0;
       background:var(--bg);z-index:10;flex-wrap:wrap}
.mark{display:flex;align-items:center;gap:8px;font-weight:700;letter-spacing:.12em}
.pulse{width:9px;height:9px;border-radius:50%;background:var(--sig);position:relative}
.pulse::after{content:"";position:absolute;inset:-4px;border-radius:50%;
  border:1px solid var(--sig);opacity:0;animation:ping 2.4s ease-out infinite}
@keyframes ping{0%{opacity:.7;transform:scale(.6)}70%{opacity:0;transform:scale(1.6)}100%{opacity:0}}
@media(prefers-reduced-motion:reduce){.pulse::after{animation:none}}
.tag{color:var(--dim);font-size:10px;letter-spacing:.2em}
.status{margin-left:auto;display:flex;gap:12px;align-items:center;font-size:11px;color:var(--mut)}
.live{color:var(--sig)}
select,button.tb{background:var(--panel);color:var(--ink);border:1px solid var(--line);
  padding:3px 8px;font:inherit;font-size:11px;cursor:pointer}
main{display:grid;grid-template-columns:1fr 340px;gap:0;min-height:calc(100vh - 46px)}
@media(max-width:900px){main{grid-template-columns:1fr}}
section{border-right:1px solid var(--line);padding:14px 16px;min-width:0}
aside{padding:14px 16px;min-width:0}
h2{font-size:10px;letter-spacing:.22em;color:var(--dim);text-transform:uppercase;
   margin-bottom:10px;display:flex;gap:8px;align-items:baseline}
h2 .n{color:var(--sig)}
table{width:100%;border-collapse:collapse;font-size:12px}
th{font-size:9px;letter-spacing:.14em;color:var(--dim);text-align:left;
   padding:4px 6px;border-bottom:1px solid var(--line);text-transform:uppercase}
td{padding:5px 6px;border-bottom:1px solid var(--line);color:var(--mut);
   white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:220px}
tr{cursor:pointer}
tr:hover td{color:var(--ink)}
td.t{color:var(--ink)}
.lbl{font-size:9px;padding:1px 6px;border:1px solid var(--line);letter-spacing:.08em}
.lbl.VIRAL,.lbl.BREAKOUT{border-color:var(--sig);color:var(--sig);background:var(--sig-dim)}
.lbl.ACCELERATING{color:var(--sig)}
.lbl.EMERGING{color:var(--ink)}
.spark{height:16px;width:72px}
.spark polyline{fill:none;stroke:var(--mut);stroke-width:1}
.spark .hot polyline{stroke:var(--sig)}
#worldpulse{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px}
.geo{border:1px solid var(--line);padding:4px 9px;font-size:11px;color:var(--mut)}
.geo b{color:var(--ink)}
.geo.hot{border-color:var(--sig);color:var(--sig)}
#feed{max-height:46vh;overflow-y:auto;font-size:11.5px}
#feed div{padding:4px 0;border-bottom:1px solid var(--line);color:var(--mut)}
#feed .new{animation:in .5s ease-out}
@keyframes in{from{opacity:0;transform:translateY(-3px)}to{opacity:1}}
#detail{position:fixed;right:0;top:0;bottom:0;width:min(480px,100vw);
  background:var(--panel);border-left:1px solid var(--line);padding:18px;
  overflow-y:auto;transform:translateX(100%);transition:transform .18s ease-out;z-index:20}
#detail.open{transform:none}
#detail h3{font-size:16px;margin-bottom:4px}
.why li{color:var(--mut);margin:3px 0 3px 14px}
.prov{font-size:11px;border-top:1px solid var(--line);padding:5px 0;color:var(--mut)}
#palette{position:fixed;inset:0;background:rgba(0,0,0,.6);display:none;
  align-items:flex-start;justify-content:center;padding-top:14vh;z-index:30}
#palette.open{display:flex}
#palette>div{background:var(--panel);border:1px solid var(--line);width:min(460px,92vw)}
#palette input{width:100%;background:none;border:0;border-bottom:1px solid var(--line);
  color:var(--ink);padding:10px 12px;font:inherit;outline:none}
#palette .opt{padding:7px 12px;color:var(--mut);cursor:pointer}
#palette .opt:hover,#palette .opt.sel{background:var(--sig-dim);color:var(--sig)}
body.dense td{padding:2px 6px;font-size:11px}
body.dense #feed{font-size:10.5px}
.sim{background:var(--sig);color:#000;text-align:center;font-size:11px;
  padding:3px;letter-spacing:.15em;display:none}
footer{border-top:1px solid var(--line);padding:8px 16px;font-size:10px;
  color:var(--dim);display:flex;gap:14px;flex-wrap:wrap}
</style></head><body>
<div class="sim" id="simbanner">SIMULATED DATA — NOT REAL SIGNALS</div>
<header>
  <span class="mark"><span class="pulse"></span>ISLA</span>
  <span class="tag">LIVE MAP OF HUMAN ATTENTION</span>
  <div class="status">
    <span id="rt" class="live">● CONNECTING</span>
    <span id="stats"></span>
    <select id="sort"><option value="opportunity">opportunity</option>
      <option value="rising">rising</option><option value="engagement">volume</option></select>
    <button class="tb" id="view-t">TRENDS</button>
    <button class="tb" id="view-e">EMERGING</button>
    <button class="tb" id="view-s">SYSTEM</button>
    <button class="tb" id="density">DENSE</button>
    <button class="tb" onclick="openPalette()">⌘K</button>
  </div>
</header>
<main>
  <section>
    <h2><span class="n">01</span> WORLD PULSE <span id="geo-note" style="color:var(--dim)">country-level, from sources that report geography — never invented</span></h2>
    <div id="worldpulse"></div>
    <h2 id="tbl-title"><span class="n">02</span> TRENDS</h2>
    <div style="overflow-x:auto"><table id="tbl">
      <thead><tr><th>topic</th><th>state</th><th>trend</th><th>vel</th>
        <th>sources</th><th>conf</th><th>score</th></tr></thead>
      <tbody></tbody></table></div>
    <div id="system" style="display:none"></div>
  </section>
  <aside>
    <h2><span class="n">03</span> LIVE STREAM</h2>
    <div id="feed"></div>
  </aside>
</main>
<footer>
  <span>ISLA v0.2 — open source</span><span>real signals only</span>
  <span><a href="/docs">API</a></span>
  <span id="lastscan"></span>
</footer>
<div id="detail"></div>
<div id="palette"><div>
  <input id="pal-in" placeholder="search trends, jump to view, change timeframe…">
  <div id="pal-opts"></div>
</div></div>
<script>
let TRENDS=[],VIEW='trends';
const $=s=>document.querySelector(s);
function spark(series,hot){if(!series||series.length<2)return'';
  const w=72,h=16,mx=Math.max(...series),mn=Math.min(...series),r=mx-mn||1;
  const pts=series.map((v,i)=>`${(i/(series.length-1))*w},${h-2-((v-mn)/r)*(h-4)}`).join(' ');
  return`<svg class="spark"><g${hot?' class="hot"':''}><polyline points="${pts}"/></g></svg>`}
function render(){
  const tb=$('#tbl tbody');tb.innerHTML='';
  TRENDS.forEach(t=>{
    const hot=['BREAKOUT','VIRAL'].includes(t.label);
    const v=t.velocity_pct==null?'baseline…':(t.velocity_pct>0?'+':'')+t.velocity_pct+'%';
    const tr=document.createElement('tr');
    tr.innerHTML=`<td class="t">${t.topic}</td>
      <td><span class="lbl ${t.label}">${t.label}</span></td>
      <td>${spark(t.series,hot)}</td><td>${v}</td>
      <td>${(t.sources||[]).length}</td><td>${t.confidence||''}</td>
      <td style="color:${hot?'var(--sig)':'var(--ink)'}">${t.opportunity}</td>`;
    tr.onclick=()=>openDetail(t.id);tb.appendChild(tr)});
  const geo={};TRENDS.forEach(t=>(t.regions||[]).forEach(r=>{geo[r]=(geo[r]||0)+t.opportunity}));
  const wp=$('#worldpulse');wp.innerHTML='';
  Object.entries(geo).sort((a,b)=>b[1]-a[1]).forEach(([r,v])=>{
    const d=document.createElement('span');d.className='geo'+(v>150?' hot':'');
    d.innerHTML=`<b>${r}</b> ${Math.round(v)}`;wp.appendChild(d)});
  if(!Object.keys(geo).length)wp.innerHTML='<span class="geo">no geographic signals yet — sources with geo: google_trends, wikipedia</span>'}
async function load(){
  const sort=$('#sort').value;
  const url=VIEW==='emerging'?'/api/v1/emerging':`/api/v1/trends?sort=${sort}`;
  TRENDS=await(await fetch(url)).json();render();
  const st=await(await fetch('/api/v1/stats')).json();
  $('#stats').textContent=`${st.topics_live} topics · ${st.events_per_min}/min`;
  $('#lastscan').textContent=st.last_scan?`last scan ${new Date(st.last_scan).toLocaleTimeString()} (${st.last_scan_ms}ms)`:'no scan yet';
  const sim=TRENDS.some(t=>t.simulated);$('#simbanner').style.display=sim?'block':'none'}
async function openDetail(id){
  const d=await(await fetch('/api/v1/trends/'+id)).json();
  $('#detail').innerHTML=`<button class="tb" onclick="$('#detail').classList.remove('open')" style="float:right">✕</button>
    <h3>${d.topic}</h3>
    <p><span class="lbl ${d.label}">${d.label}</span>
       <span style="color:var(--dim)"> ${d.lifecycle} · first seen ${new Date(d.first_seen).toLocaleString()}</span></p>
    <h2 style="margin-top:14px">WHY IS THIS TRENDING?</h2>
    <ul class="why">${(d.why||[]).map(w=>`<li>${w}</li>`).join('')}</ul>
    <h2 style="margin-top:14px">PROVENANCE — ${d.provenance.length} traced signals</h2>
    ${d.provenance.map(e=>`<div class="prov">[${e.source}] ${e.simulated?'<b>SIM</b> ':''}
      <a href="${e.url}" target="_blank" rel="noreferrer">${e.title||e.url}</a>
      · ${Math.round(e.engagement)} · ${e.region||''}</div>`).join('')}`;
  $('#detail').classList.add('open')}
async function showSystem(){
  const src=await(await fetch('/api/v1/sources')).json();
  const st=await(await fetch('/api/v1/stats')).json();
  $('#tbl').style.display='none';$('#worldpulse').style.display='none';
  $('#tbl-title').style.display='none';
  const sys=$('#system');sys.style.display='block';
  sys.innerHTML='<h2><span class="n">02</span> CONNECTOR HEALTH — real states, no fake numbers</h2>'+
   '<table><thead><tr><th>connector</th><th>state</th><th>items</th><th>latency</th><th>freshness</th></tr></thead><tbody>'+
   Object.entries(src).map(([k,v])=>`<tr><td class="t">${k}</td>
     <td><span class="lbl ${v.state==='HEALTHY'?'EMERGING':''}" style="${v.state!=='HEALTHY'&&v.state!=='UNKNOWN'?'color:#E0564F;border-color:#E0564F':''}">${v.state}</span></td>
     <td>${v.items??'—'}</td><td>${v.latency_ms?v.latency_ms+'ms':'—'}</td>
     <td style="max-width:none;white-space:normal">${v.freshness}${v.error?' · '+v.error:''}</td></tr>`).join('')+
   `</tbody></table><p style="margin-top:10px;color:var(--dim)">scan interval ${st.scan_interval_s}s ·
    ${st.realtime_listeners} realtime listener(s) · ${st.samples_total} samples stored</p>`}
function showTrends(em){VIEW=em?'emerging':'trends';
  $('#system').style.display='none';$('#tbl').style.display='';
  $('#worldpulse').style.display='';$('#tbl-title').style.display='';
  $('#tbl-title').innerHTML=`<span class="n">02</span> ${em?'EMERGING — what might go viral next':'TRENDS'}`;load()}
$('#view-t').onclick=()=>showTrends(false);
$('#view-e').onclick=()=>showTrends(true);
$('#view-s').onclick=showSystem;
$('#sort').onchange=load;
$('#density').onclick=()=>{document.body.classList.toggle('dense');
  $('#density').textContent=document.body.classList.contains('dense')?'FOCUS':'DENSE'};
// SSE realtime
function connect(){
  const es=new EventSource('/api/v1/stream');
  es.onopen=()=>{$('#rt').textContent='● LIVE'};
  es.onerror=()=>{$('#rt').textContent='● RECONNECTING';es.close();setTimeout(connect,3000)};
  es.onmessage=ev=>{const d=JSON.parse(ev.data);
    if(d.type==='scan.completed'){
      const f=$('#feed');const row=document.createElement('div');row.className='new';
      row.textContent=`${new Date().toLocaleTimeString()} scan: ${d.signals} signals → ${d.topics} topics`;
      f.prepend(row);while(f.children.length>60)f.lastChild.remove();
      (d.top||[]).slice(0,5).forEach(t=>{if(['BREAKOUT','VIRAL','ACCELERATING'].includes(t.label)){
        const r2=document.createElement('div');r2.className='new';
        r2.innerHTML=`<span style="color:var(--sig)">${t.label}</span> ${t.topic} [${t.opportunity}]`;
        f.prepend(r2)}});
      if(VIEW!=='system')load()}
    if(d.type==='scan.error'){const f=$('#feed');const row=document.createElement('div');
      row.textContent='scan error: '+d.error;f.prepend(row)}}}
connect();
// Cmd+K palette
const CMDS=[['Open trends',()=>showTrends(false)],['Open emerging',()=>showTrends(true)],
  ['Open system',showSystem],['Toggle density',()=>$('#density').click()],
  ['Sort by rising',()=>{$('#sort').value='rising';load()}],
  ['Sort by opportunity',()=>{$('#sort').value='opportunity';load()}]];
function openPalette(){$('#palette').classList.add('open');
  const inp=$('#pal-in');inp.value='';renderPal('');inp.focus()}
function renderPal(q){const opts=$('#pal-opts');opts.innerHTML='';
  const items=[...CMDS.filter(([l])=>l.toLowerCase().includes(q)),
    ...TRENDS.filter(t=>t.topic.includes(q)).slice(0,6).map(t=>['» '+t.topic,()=>openDetail(t.id)])];
  items.slice(0,10).forEach(([l,fn],i)=>{const d=document.createElement('div');
    d.className='opt'+(i===0?' sel':'');d.textContent=l;
    d.onclick=()=>{fn();$('#palette').classList.remove('open')};opts.appendChild(d)})}
$('#pal-in').oninput=e=>renderPal(e.target.value.toLowerCase());
document.addEventListener('keydown',e=>{
  if((e.metaKey||e.ctrlKey)&&e.key==='k'){e.preventDefault();openPalette()}
  if(e.key==='Escape'){$('#palette').classList.remove('open');$('#detail').classList.remove('open')}
  if(e.key==='Enter'&&$('#palette').classList.contains('open')){
    const sel=$('#pal-opts .opt.sel');if(sel)sel.click()}});
$('#palette').onclick=e=>{if(e.target.id==='palette')e.target.classList.remove('open')};
load();
</script></body></html>"""
