const office=document.querySelector('#office'),missions=document.querySelector('#missions'),
timeline=document.querySelector('#timeline'),attention=document.querySelector('#attention'),
attentionCard=document.querySelector('#attention-card'),metrics=document.querySelector('#metrics'),
connection=document.querySelector('#connection'),needs=document.querySelector('#needs'),
dialog=document.querySelector('#agent-dialog'),detail=document.querySelector('#agent-detail');
let latest=null;

function esc(v){return String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));}
function labelStatus(s){return ({working:'trabalhando',idle:'disponível',planned:'planejado',error:'erro',needs_input:'precisa de você'})[s]||s;}
function fmtTime(ts){if(!ts)return '';try{return new Date(ts).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'})}catch{return ''}}

function avatar(a){
  const p=Math.round((a.progress||0)*100);
  return `<button class="desk ${esc(a.status)}" data-agent="${esc(a.id)}">
    <div class="agent-tag">${esc(a.name)}</div>
    <div class="desk-stage">
      <div class="desk-surface"><div class="screen"></div></div>
      <div class="person"><i class="beacon"></i><div class="hair"></div><div class="head"></div><div class="body"></div><div class="legs"></div></div>
    </div>
    <div class="activity">${esc(a.activity||labelStatus(a.status))}</div>
    ${a.status==='working'?`<div class="progress"><i style="width:${p}%"></i></div>`:''}
  </button>`;
}
function renderRoom(name,agents){
  return `<article class="room" data-dept="${esc(name)}"><div class="room-head"><h3>${esc(name)}</h3><span class="count">${agents.length}</span></div><div class="desks">${agents.map(avatar).join('')}</div></article>`;
}
function showAgent(id){
  if(!latest)return;
  const a=Object.values(latest.departments).flat().find(x=>x.id===id);
  if(!a)return;
  detail.innerHTML=`<h2 class="detail-title">${esc(a.name)}</h2>
    <div class="detail-dept">${esc(a.department)} · ${esc(a.id)}</div>
    <div class="detail-grid">
      <div class="detail-box"><small>Status</small><b>${esc(labelStatus(a.status))}</b></div>
      <div class="detail-box"><small>Atividade</small><b>${esc(a.activity||'—')}</b></div>
      <div class="detail-box"><small>Modelo</small><b>${esc(a.model||'determinístico / —')}</b></div>
      <div class="detail-box"><small>Task</small><b>${esc(a.task_id||'—')}</b></div>
    </div>
    <div class="detail-mission">${esc(a.mission)}</div>`;
  dialog.showModal();
}
function step(s){return `<span class="mstep ${esc(s.status)}" title="${esc(s.agent_id)}">${esc(s.agent_id.split('.').pop())}</span>`}

async function approval(id,action){
  const r=await fetch(`/api/approval/${encodeURIComponent(id)}/${action}`,{
    method:'POST',headers:{'Content-Type':'application/json'},body:'{}'
  });
  const x=await r.json();
  if(!r.ok)alert(x.error||'Falha na aprovação.');
  await poll();
}

function render(data){
  latest=data;
  office.innerHTML=Object.entries(data.departments).map(([n,a])=>renderRoom(n,a)).join('');
  document.querySelectorAll('[data-agent]').forEach(el=>el.onclick=()=>showAgent(el.dataset.agent));
  metrics.innerHTML=`<div class="metric"><b>${data.metrics.agents_available}/${data.metrics.agents_total}</b><small>operacionais</small></div><div class="metric"><b>${data.metrics.agents_working}</b><small>trabalhando</small></div><div class="metric"><b>${data.metrics.missions_active}</b><small>missões</small></div><div class="metric"><b>${data.metrics.inbox_unread||0}</b><small>inbox</small></div>`;
  needs.textContent=`${data.metrics.needs_you} precisam de você`;
  needs.classList.toggle('hidden',!data.metrics.needs_you);
  attentionCard.classList.toggle('hidden',!data.attention.length);
  attention.innerHTML=data.attention.map(x=>`<div class="attention-item">
    <strong>${esc(x.title)}</strong><span>${esc(x.kind)} · ${esc(x.risk)}</span>
    ${x.kind==='approval'?`<div class="approval-actions"><button class="approve" onclick="approval('${esc(x.id)}','approve')">Aprovar</button><button class="reject" onclick="approval('${esc(x.id)}','reject')">Rejeitar</button></div>`:''}
  </div>`).join('');
  missions.innerHTML=data.missions.length?data.missions.map(m=>`<div class="mission"><strong>${esc(m.title)}</strong><span>${esc(m.status)}</span><div class="msteps">${(m.steps||[]).map(step).join('')}</div></div>`).join(''):'Nenhuma missão ainda.';
  timeline.innerHTML=data.timeline.slice(0,22).map(e=>`<div class="event"><time>${fmtTime(e.timestamp)}</time><div><div class="kind">${esc(e.type)}</div><div class="who">${esc(e.agent_id||e.task_id||'sistema')}</div></div></div>`).join('');
}
async function poll(){
  try{
    const r=await fetch('/api/hq',{cache:'no-store'});
    if(!r.ok)throw Error(r.status);
    render(await r.json());
    connection.textContent='online';connection.classList.add('online');
  }catch{
    connection.textContent='desconectado';connection.classList.remove('online');
  }
}
window.approval=approval;
poll();setInterval(poll,700);
