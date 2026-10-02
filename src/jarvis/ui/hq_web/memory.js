const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
async function load(){
 const x=await fetch('/api/memory').then(r=>r.json());
 $('#memory').innerHTML=x.length?x.map(m=>`<div class="row"><b>${esc(m.memory_type)} · importância ${Number(m.importance||0).toFixed(2)}</b><small>${esc(m.content)}</small><small>origem: ${esc(m.source)} · confiança ${Number(m.confidence||0).toFixed(2)}</small></div>`).join(''):'<div class="empty">Nenhuma memória persistente.</div>';
}
$('#refresh').onclick=load;load();
