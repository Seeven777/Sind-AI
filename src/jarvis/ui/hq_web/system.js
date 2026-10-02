const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
function badge(s){return `<span class="badge ${esc(s)}">${esc(s)}</span>`}
function rows(obj){
 return Object.entries(obj||{}).map(([k,v])=>`<div class="row"><b>${esc(k)} ${badge(v.status||'unknown')}</b><small>${esc(v.error||v.backend||v.base_url||'')}</small></div>`).join('');
}
async function load(){
 const x=await fetch('/api/system').then(r=>r.json());
 $('#core').innerHTML=`<div class="row"><b>Foundation ${badge(x.foundation.status)}</b><small>${esc(x.foundation.run_id)}</small></div>`;
 $('#models').innerHTML=rows(x.models);
 $('#connectors').innerHTML=rows(x.connectors);
 $('#google').innerHTML=`<div class="row"><b>${badge(x.google.status)}</b><small>${esc(x.google.client_config||x.google.error||'')}</small></div>`;
 $('#computer').innerHTML=`<div class="row"><b>Browser ${badge(x.browser.status)}</b><small>${esc(x.browser.backend||'')}</small></div><div class="row"><b>Windows UIA ${badge(x.windows.status)}</b><small>${esc(x.windows.backend||'')}</small></div>`;
 $('#voice').innerHTML=rows(x.voice);
 $('#skills').innerHTML=x.skills.length?x.skills.map(s=>`<div class="row"><b>${esc(s.skill_id)} ${badge(s.state)}</b><small>${esc(s.version)}</small></div>`).join(''):'<div class="empty">Nenhuma skill instalada.</div>';
 $('#caps').textContent=JSON.stringify(x.capabilities,null,2);
}
$('#sync').onclick=async()=>{await fetch('/api/connectors/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});load()};
$('#gauth').onclick=async()=>{const r=await fetch('/api/google/auth',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});const x=await r.json();if(!r.ok)alert(x.error||'Falha Google');load()};
$('#gdisconnect').onclick=async()=>{await fetch('/api/google/disconnect',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});load()};
load();setInterval(load,5000);
