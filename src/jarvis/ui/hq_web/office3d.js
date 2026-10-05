const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
const canvas=$('#scene'),ctx=canvas.getContext('2d',{alpha:false,desynchronized:true}),world=$('#world'),labels=$('#labels');
if(!ctx)throw new Error('Canvas indisponível');
const ROOMS=[
{name:'Research',x:-420,y:-245,w:330,h:185,c:'#70caff',d:'Pesquisa e evidência'},
{name:'Intelligence',x:0,y:-245,w:330,h:185,c:'#8ba6ff',d:'Análise e decisão'},
{name:'Creative',x:420,y:-245,w:330,h:185,c:'#d99ed7',d:'Criação e planejamento'},
{name:'Engineering',x:-420,y:15,w:330,h:185,c:'#77baff',d:'Código e arquitetura'},
{name:'Command',x:0,y:15,w:330,h:185,c:'#77e1ff',d:'Orquestração central'},
{name:'Operations',x:420,y:15,w:330,h:185,c:'#70ddb5',d:'Execução verificada'},
{name:'Review',x:-420,y:275,w:330,h:185,c:'#c39cf3',d:'Qualidade e validação'},
{name:'Administration',x:0,y:275,w:330,h:185,c:'#e1bc77',d:'Inbox e conectores'},
{name:'Memory',x:420,y:275,w:330,h:185,c:'#8dbbff',d:'Contexto persistente'}];
const MAP=Object.fromEntries(ROOMS.map(r=>[r.name,r]));
const SLOTS=[[.29,.47],[.71,.47],[.50,.69]];
let state=null,selected={type:'command',id:'Command'},camera={x:0,y:12,zoom:.92},target={...camera},drag=null,auto=false,pulse=0,last=performance.now(),labelsEnabled=true;
const clamp=(n,a,b)=>Math.max(a,Math.min(b,n)),lerp=(a,b,t)=>a+(b-a)*t;
function rgba(h,a=1){let c=h.slice(1);if(c.length===3)c=c.split('').map(x=>x+x).join('');let n=parseInt(c,16);return`rgba(${n>>16&255},${n>>8&255},${n&255},${a})`}
function resize(){const r=world.getBoundingClientRect(),d=Math.min(devicePixelRatio||1,2);canvas.width=Math.max(1,r.width*d);canvas.height=Math.max(1,r.height*d);canvas.style.width=r.width+'px';canvas.style.height=r.height+'px';ctx.setTransform(d,0,0,d,0,0)}
function proj(x,y,z=0){const w=world.clientWidth,h=world.clientHeight,s=target.zoom;return{x:w/2+(x-target.x)*s,y:h/2+(y-target.y)*s*.72-z*s}}
function roomData(r){const p=proj(r.x,r.y);return{x:p.x,y:p.y,w:r.w*target.zoom,h:r.h*target.zoom*.72,depth:28*target.zoom}}
function agentsFor(rn){return(state?.departments?.[rn]||[]).slice(0,3).map((a,i)=>({...a,_slot:SLOTS[i]}))}
function allAgents(){return Object.values(state?.departments||{}).flat()}
function findAgent(id){return allAgents().find(a=>a.id===id)}
function roomOf(id){return ROOMS.find(r=>agentsFor(r.name).some(a=>a.id===id))?.name}
function fit(){target={x:0,y:18,zoom:.92};selected={type:'command',id:'Command'}}
function focusRoom(n){const r=MAP[n];if(!r)return;target={x:r.x+r.w/2,y:r.y+r.h/2-40,zoom:1.35};selected={type:'room',id:n}}
function focusAgent(id){const rn=roomOf(id);const r=MAP[rn];const a=agentsFor(rn).find(x=>x.id===id);if(!r||!a)return;target={x:r.x+r.w*a._slot[0],y:r.y+r.h*a._slot[1]-25,zoom:1.55};selected={type:'agent',id}}
function drawPoly(p,fill,stroke,w=1){ctx.beginPath();ctx.moveTo(p[0][0],p[0][1]);for(let i=1;i<p.length;i++)ctx.lineTo(p[i][0],p[i][1]);ctx.closePath();if(fill){ctx.fillStyle=fill;ctx.fill()}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=w;ctx.stroke()}}
function rr(x,y,w,h,r,fill,stroke){ctx.beginPath();ctx.roundRect(x,y,w,h,r);if(fill){ctx.fillStyle=fill;ctx.fill()}if(stroke){ctx.strokeStyle=stroke;ctx.stroke()}}
function shadowEllipse(x,y,rx,ry,a=.22){ctx.save();ctx.fillStyle=`rgba(0,0,0,${a})`;ctx.beginPath();ctx.ellipse(x,y,rx,ry,0,0,Math.PI*2);ctx.fill();ctx.restore()}
function room(r){const s=roomData(r),isSel=selected.type==='room'&&selected.id===r.name,work=agentsFor(r.name).filter(a=>a.status==='working').length;
 // floor slab
 rr(s.x,s.y,s.w,s.h,10,isSel?rgba(r.c,.10):'#08131c',isSel?rgba(r.c,.68):'#1c3340');
 // raised back wall / side depth for the 3D feel
 drawPoly([[s.x,s.y],[s.x+s.w,s.y],[s.x+s.w,s.y+14*s.depth/28],[s.x,s.y+14*s.depth/28]],rgba(r.c,.03),rgba(r.c,.25));
 drawPoly([[s.x+s.w,s.y],[s.x+s.w+10*s.depth/28,s.y-10*s.depth/28],[s.x+s.w+10*s.depth/28,s.y+s.h-10*s.depth/28],[s.x+s.w,s.y+s.h]],rgba(r.c,.06),rgba(r.c,.22));
 ctx.save();ctx.strokeStyle=rgba(r.c,isSel?.48:.12);ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(s.x+8,s.y+8);ctx.lineTo(s.x+s.w-8,s.y+8);ctx.stroke();ctx.restore();
 ctx.fillStyle='#8ea4ad';ctx.font='600 7px Inter,Segoe UI,Arial';ctx.fillText(r.name.toUpperCase(),s.x+12,s.y+22);ctx.fillStyle='#4f6672';ctx.font='6px Inter,Segoe UI,Arial';ctx.fillText(r.d,s.x+12,s.y+33);
 if(work){rr(s.x+s.w-50,s.y+10,39,14,7,rgba(r.c,.10),rgba(r.c,.30));ctx.fillStyle=r.c;ctx.font='600 5px Inter,Segoe UI,Arial';ctx.fillText(work+' WORKING',s.x+s.w-44,s.y+19)}
 // floor grid
 ctx.save();ctx.strokeStyle='#10242e';ctx.lineWidth=.6;for(let i=1;i<4;i++){ctx.beginPath();ctx.moveTo(s.x+11,s.y+s.h*i/4);ctx.lineTo(s.x+s.w-11,s.y+s.h*i/4);ctx.stroke()}ctx.restore();
}
function desk(x,y,c,a){const z=target.zoom,working=a?.status==='working';shadowEllipse(x,y+22*z,31*z,7*z,.3);rr(x-32*z,y-7*z,64*z,25*z,6,'#0a171f','#24414e');rr(x-19*z,y-25*z,38*z,21*z,4,'#061017','#2a4b5c');const gg=working?rgba(c,.18):rgba(c,.06);rr(x-15*z,y-21*z,30*z,13*z,3,gg);ctx.fillStyle=working?c:'#526b77';ctx.font=`600 ${Math.max(5,5.5*z)}px Inter,Segoe UI,Arial`;ctx.fillText((a?.name||'AGENT').slice(0,11),x-13*z,y-12*z);rr(x-15*z,y+2*z,30*z,5*z,2,'#101c23','#1c3039');ctx.fillStyle='#0f1b23';ctx.beginPath();ctx.ellipse(x,y+31*z,10*z,5*z,0,0,Math.PI*2);ctx.fill();
 // agent avatar with subtle bob
 const bob=working?Math.sin(pulse*.004+(x*.01))*1.8:0;ctx.save();ctx.shadowBlur=working?14:0;ctx.shadowColor=c;ctx.fillStyle=working?c:'#516f7d';ctx.beginPath();ctx.arc(x,y-34*z+bob,6*z,0,Math.PI*2);ctx.fill();ctx.fillStyle='#071017';ctx.beginPath();ctx.arc(x-2*z,y-36*z+bob,1*z,0,Math.PI*2);ctx.arc(x+2*z,y-36*z+bob,1*z,0,Math.PI*2);ctx.fill();ctx.restore();
 return {x,y:y-43*z}
}
function link(a,b,c,active){ctx.save();ctx.strokeStyle=rgba(c,active?.34:.08);ctx.lineWidth=active?1.8:.7;ctx.setLineDash(active?[6,8]:[]);ctx.lineDashOffset=-(pulse*.04);ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();if(active){const t=(pulse*.0018)%1,x=a.x+(b.x-a.x)*t,y=a.y+(b.y-a.y)*t;ctx.fillStyle=c;ctx.shadowBlur=10;ctx.shadowColor=c;ctx.beginPath();ctx.arc(x,y,2.3,0,Math.PI*2);ctx.fill()}ctx.restore()}
function core(){const r=MAP.Command,s=roomData(r),x=s.x+s.w/2,y=s.y+s.h*.51;const glow=ctx.createRadialGradient(x,y,0,x,y,95*target.zoom);glow.addColorStop(0,'rgba(119,225,255,.22)');glow.addColorStop(1,'rgba(119,225,255,0)');ctx.fillStyle=glow;ctx.fillRect(x-120,y-120,240,240);rr(x-64*target.zoom,y-21*target.zoom,128*target.zoom,55*target.zoom,11,'#07151e','#3e6e82');ctx.fillStyle='#9beeff';ctx.font=`700 ${Math.max(7,8*target.zoom)}px Inter,Segoe UI,Arial`;ctx.fillText('COMMAND CORE',x-43*target.zoom,y-3*target.zoom);ctx.fillStyle='#5d7886';ctx.font=`${Math.max(5,5.5*target.zoom)}px Inter,Segoe UI,Arial`;ctx.fillText('router · planner · verifier',x-45*target.zoom,y+11*target.zoom)}
function render(){const now=performance.now(),dt=Math.min(50,now-last);last=now;pulse+=dt;if(auto){const t=now*.000045;target.x=Math.sin(t)*45;target.y=20+Math.cos(t)*10;target.zoom=.93+Math.sin(t)*.035}camera.x=lerp(camera.x,target.x,.12);camera.y=lerp(camera.y,target.y,.12);camera.zoom=lerp(camera.zoom,target.zoom,.12);
 const w=world.clientWidth,h=world.clientHeight;const bg=ctx.createLinearGradient(0,0,0,h);bg.addColorStop(0,'#07131c');bg.addColorStop(1,'#03070c');ctx.fillStyle=bg;ctx.fillRect(0,0,w,h);
 // ambient grid
 ctx.save();ctx.globalAlpha=.3;ctx.strokeStyle='#14303d';ctx.lineWidth=.55;const step=34*camera.zoom,ox=((camera.x*camera.zoom)%step+step)%step,oy=((camera.y*camera.zoom)%step+step)%step;for(let x=ox;x<w;x+=step){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke()}for(let y=oy;y<h;y+=step){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke()}ctx.restore();
 // floor base
 const f=proj(0,230,-12);drawPoly([[f.x-680*camera.zoom,f.y],[f.x+680*camera.zoom,f.y],[f.x+680*camera.zoom,f.y+85*camera.zoom],[f.x-680*camera.zoom,f.y+85*camera.zoom]],'#07131b','#132a35');
 // cables first
 const c=roomData(MAP.Command),cp={x:c.x+c.w/2,y:c.y+c.h/2};for(const r of ROOMS){if(r.name==='Command')continue;const s=roomData(r);link(cp,{x:s.x+s.w/2,y:s.y+s.h/2},r.c,agentsFor(r.name).some(a=>a.status==='working'))}
 ROOMS.forEach(room);core();
 const tag=[];for(const r of ROOMS){for(const a of agentsFor(r.name)){const s=roomData(r),p=desk(s.x+s.w*a._slot[0],s.y+s.h*a._slot[1],r.c,a);const lp=proj(r.x+r.w*a._slot[0],r.y+r.h*a._slot[1]-52);tag.push({a,x:lp.x,y:lp.y,working:a.status==='working',sel:selected.type==='agent'&&selected.id===a.id})}}
 const visible=labelsEnabled?tag:[];labels.innerHTML=visible.map(t=>`<div class="agent-label ${t.working?'working':''}" style="left:${t.x}px;top:${t.y}px"><div class="line"><i></i><b>${esc(t.a.name)}</b></div><small>${esc(t.a.model||'modelo não informado')} · ${esc(t.a.activity||'Disponível')}</small></div>`).join('');
 $('#clock').textContent=new Date().toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit',second:'2-digit'});requestAnimationFrame(render)}
function updateUI(){const ag=allAgents(),work=ag.filter(a=>a.status==='working'),tasks=state?.tasks||[],att=state?.attention||[],mis=state?.missions||[];$('#stats').innerHTML=[['working',work.length],['tasks',tasks.length],['attention',att.length],['missions',mis.filter(m=>!['completed','failed','cancelled'].includes(m.status)).length]].map(x=>`<div class="stat"><b>${x[1]}</b><span>${x[0]}</span></div>`).join('');$('#working-total').textContent=work.length;
 const sa=selected.type==='agent'?findAgent(selected.id):null;$('#selection-title').textContent=sa?.name||selected.id||'Command Core';$('#selection-sub').textContent=sa?.department||'Orquestração central';$('#node-name').textContent=sa?.name||'Command Core';$('#node-role').textContent=sa?.mission||'Central orchestration';$('#node-meta').textContent=sa?`${sa.model||'modelo não informado'} · ${sa.department}`:'sistema · coordinator';$('#node-activity').textContent=sa?.activity||'Selecione uma estação para acompanhar exatamente o trabalho atual.';const st=sa?.status||'idle';$('#node-badge').textContent=String(st).toUpperCase();$('#node-badge').style.color=st==='working'?'#7bdcff':st==='error'?'#ef7380':'#84bbcf';const pr=Math.round((sa?.progress||0)*100);$('#node-progress').textContent=pr+'%';$('#node-bar').style.width=pr+'%';
 const task=sa?.task_id?tasks.find(t=>t.id===sa.task_id):null;const tb=$('#node-task');if(task){tb.classList.remove('hidden');tb.innerHTML=`<b>${esc(task.title)}</b><span>${esc(task.status)} · checkpoint ${esc(task.checkpoint||0)}</span>`;$('#task-badge').textContent=String(task.status).toUpperCase();$('#task').classList.remove('empty');$('#task').innerHTML=`<b>${esc(task.title)}</b>${esc(task.objective||'')}<br><code>${esc(task.id)}</code>`}else{tb.classList.add('hidden');$('#task-badge').textContent='—';$('#task').classList.add('empty');$('#task').textContent='Nenhuma tarefa vinculada.'}
 $('#working').innerHTML=work.length?work.map(a=>{const p=Math.round((a.progress||0)*100);return`<div class="work-row" data-agent="${esc(a.id)}"><div class="work-top"><b>${esc(a.name)}</b><small>${esc(a.model||'modelo')}</small></div><div class="work-activity">${esc(a.activity||'Trabalhando')}</div><div class="work-meta"><span>${esc(a.department)}</span><b>${p}%</b></div><div class="mini"><i style="width:${p}%"></i></div></div>`}).join(''):`<div class="task-detail empty">Nenhum agente trabalhando agora.</div>`;
 const depts=state?.departments||{};$('#departments').innerHTML=ROOMS.map(r=>`<button class="dep ${selected.type==='room'&&selected.id===r.name?'active':''}" data-room="${r.name}"><b>${r.name}</b><span>${(depts[r.name]||[]).length} agente(s) · ${esc(r.d)}</span></button>`).join('');document.querySelectorAll('[data-agent]').forEach(e=>e.onclick=()=>{selected={type:'agent',id:e.dataset.agent};focusAgent(e.dataset.agent);showToast('Agente focado');updateUI()});document.querySelectorAll('[data-room]').forEach(e=>e.onclick=()=>{focusRoom(e.dataset.room);showToast(e.dataset.room);updateUI()});
 const flow=(state?.timeline||[]).filter(e=>e.agent_id||e.task_id).slice(0,6);$('#flow').innerHTML=flow.length?flow.map(e=>`<div class="flow-chip"><i></i><div class="flow-copy"><b>${esc(e.type)}</b><small>${esc(e.agent_id||e.task_id||'system')} · ${esc(e.timestamp||'')}</small></div></div>`).join(''):`<div class="flow-chip"><i></i><div class="flow-copy"><b>Sem atividade recente</b><small>Eventos do runtime aparecerão aqui.</small></div></div>`}
async function sync(){try{const r=await fetch('/api/hq',{cache:'no-store'});if(!r.ok)throw new Error(r.status);state=await r.json();$('#connection').textContent='LIVE';$('#sync-age').textContent='SYNC';updateUI()}catch(e){$('#connection').textContent='OFFLINE';$('#sync-age').textContent='—'}setTimeout(sync,2000)}
canvas.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,cam:{...target}};world.classList.add('dragging');canvas.setPointerCapture(e.pointerId)});canvas.addEventListener('pointermove',e=>{if(!drag)return;const z=target.zoom;target.x=drag.cam.x-(e.clientX-drag.x)/z;target.y=drag.cam.y-(e.clientY-drag.y)/(z*.72)});canvas.addEventListener('pointerup',e=>{drag=null;world.classList.remove('dragging');canvas.releasePointerCapture?.(e.pointerId)});canvas.addEventListener('pointercancel',()=>{drag=null;world.classList.remove('dragging')});canvas.addEventListener('wheel',e=>{e.preventDefault();target.zoom=clamp(target.zoom*(e.deltaY<0?1.08:.92),.58,1.8)},{passive:false});
canvas.addEventListener('click',e=>{if(drag)return;const r=canvas.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;let best=null,bd=23;for(const rn of ROOMS){for(const a of agentsFor(rn.name)){const s=roomData(rn),p=proj(rn.x+rn.w*a._slot[0],rn.y+rn.h*a._slot[1]-52),d=Math.hypot(p.x-mx,p.y-my);if(d<bd){best=a;bd=d}}}if(best){selected={type:'agent',id:best.id};focusAgent(best.id);updateUI()}});
document.querySelectorAll('.controls button[data-view]').forEach(b=>b.onclick=()=>{document.querySelectorAll('.controls button').forEach(x=>x.classList.remove('active'));b.classList.add('active');const v=b.dataset.view;if(v==='overview')fit();if(v==='command'){target={x:0,y:80,zoom:1.22};selected={type:'room',id:'Command'}}if(v==='working'){const w=allAgents().find(a=>a.status==='working');if(w)focusAgent(w.id);else fit()}updateUI()});
$('#auto').onclick=()=>{auto=!auto;$('#auto').classList.toggle('active',auto);showToast(auto?'Auto tour ativo':'Auto tour pausado')};$('#reset').onclick=()=>{auto=false;$('#auto').classList.remove('active');fit();updateUI()};new ResizeObserver(resize).observe(world);resize();fit();sync();render();
function showToast(t){const e=$('#toast');e.textContent=t;e.classList.add('show');clearTimeout(showToast.t);showToast.t=setTimeout(()=>e.classList.remove('show'),800)}
