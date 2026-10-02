const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
function badge(s){return `<span class="badge ${esc(s)}">${esc(s)}</span>`}
async function load(){
 const [h,t]=await Promise.all([fetch('/api/hq').then(r=>r.json()),fetch('/api/tool-runs').then(r=>r.json())]);
 $('#missions').innerHTML=h.missions.length?h.missions.map(m=>`<div class="row"><b>${esc(m.title)} ${badge(m.status)}</b><small>${esc(m.objective)}</small><div>${(m.steps||[]).map(s=>`<span class="badge ${esc(s.status)}">${esc(s.agent_id)} · ${esc(s.status)}</span>`).join(' ')}</div></div>`).join(''):'<div class="empty">Nenhuma missão.</div>';
 $('#attention').innerHTML=h.attention.length?h.attention.map(a=>`<div class="row"><b>${esc(a.title)}</b><small>${esc(a.kind)} · ${esc(a.risk)}</small></div>`).join(''):'<div class="empty">Nada aguardando você.</div>';
 $('#tools').innerHTML=t.length?t.slice(0,20).map(x=>`<div class="row"><b>${esc(x.tool_id)} ${badge(x.status)}</b><small>${esc(x.started_at)} · ${esc(x.error||'sem erro')}</small></div>`).join(''):'<div class="empty">Nenhuma execução.</div>';
 $('#events').innerHTML=h.timeline.slice(0,25).map(e=>`<div class="row"><b>${esc(e.type)}</b><small>${esc(e.agent_id||e.task_id||'sistema')} · ${esc(e.timestamp)}</small></div>`).join('');
}
$('#refresh').onclick=load;load();setInterval(load,2000);
