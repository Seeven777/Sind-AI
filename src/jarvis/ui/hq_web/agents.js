const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
async function load(){
 const agents=await fetch('/api/agents').then(r=>r.json());
 $('#agents').innerHTML=agents.map(a=>`<section class="card span4"><div class="card-head"><h2>${esc(a.name)}</h2><span class="badge ${esc(a.status)}">${esc(a.status)}</span></div><div class="row"><b>${esc(a.department)}</b><small>${esc(a.id)}</small></div><div class="row"><b>Missão</b><small>${esc(a.mission)}</small></div><div class="row"><b>Atividade</b><small>${esc(a.activity||'—')}</small></div><div class="row"><b>Capacidades</b><small>${esc((a.capabilities||[]).join(' · '))}</small></div></section>`).join('');
}
load();setInterval(load,2500);
