const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
async function load(){const x=await fetch('/api/projects').then(r=>r.json());$('#projects').innerHTML=x.length?x.map(p=>`<div class="row"><b>${esc(p.name)} <span class="badge ${esc(p.status)}">${esc(p.status)}</span></b><small>${esc(p.objective||'Sem objetivo')}</small></div>`).join(''):'<div class="empty">Nenhum projeto.</div>'}
$('#form').onsubmit=async e=>{e.preventDefault();const r=await fetch('/api/project',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('#name').value,objective:$('#objective').value})});const x=await r.json();if(!r.ok)return alert(x.error||'Erro');e.target.reset();load()};
$('#refresh').onclick=load;load();
