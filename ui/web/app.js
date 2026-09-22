let bridge=null,snapshot=null,busy=false;
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));

function setBusy(value,detail=''){
  busy=!!value;document.body.classList.toggle('busy',busy);
  $('sendBtn').disabled=busy;$('promptInput').disabled=busy;$('cancelBtn').classList.toggle('visible',busy);
  if(detail)$('statusText').textContent=detail;
  if(!busy)$('statusText').textContent='pronto';
}
function hideWelcome(){const w=$('welcome');if(w)w.style.display='none'}
function addMessage(role,text,ok=true,time=null){
  hideWelcome();const el=document.createElement('div');el.className=`message ${role}`;
  el.innerHTML=`<div class="avatar">${role==='user'?'V':'✦'}</div><div><div class="message-head">${role==='user'?'Você':'Jarvis'}</div><div class="message-body ${ok?'':'error'}">${esc(text)}</div><div class="message-meta">${esc(time||new Date().toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'}))}</div></div>`;
  $('conversation').appendChild(el);$('chatScroll').scrollTop=$('chatScroll').scrollHeight;
}
function showThinking(text='Processando'){
  removeThinking();const el=document.createElement('div');el.id='thinking';el.className='thinking';el.textContent=text;$('conversation').appendChild(el);$('chatScroll').scrollTop=$('chatScroll').scrollHeight;
}
function removeThinking(){const x=$('thinking');if(x)x.remove()}
function sendPrompt(value){
  const prompt=String(value||'').trim();if(!prompt||!bridge||busy)return;
  addMessage('user',prompt);$('promptInput').value='';resizeInput();setBusy(true,'processando');showThinking('Jarvis está decidindo a melhor forma de responder…');bridge.sendCommand(prompt);
}
function resizeInput(){const i=$('promptInput');i.style.height='auto';i.style.height=Math.min(130,i.scrollHeight)+'px'}
function fetchSnapshot(){if(bridge)bridge.getSnapshot(raw=>{try{renderSnapshot(JSON.parse(raw))}catch(e){console.error(e)}})}

function renderSnapshot(data){
  snapshot=data||{};$('footerModel').textContent=snapshot.model||'adaptive local';
  renderSessions();renderContext();renderSources();renderActivity();renderControlCenter();
}
function renderSessions(){
  const info=snapshot?.cognitive?.sessions||{};const items=info.items||[];const current=info.current;
  $('conversationList').innerHTML=items.map(s=>`<button class="conversation-item ${Number(s.id)===Number(current)?'active':''}" data-session="${s.id}" title="${esc(s.title)}">${esc(s.title||'Nova conversa')}</button>`).join('')||'<div class="conversation-item">Nenhuma conversa ainda</div>';
  document.querySelectorAll('[data-session]').forEach(btn=>btn.onclick=()=>openConversation(Number(btn.dataset.session)));
}
function openConversation(id){
  if(!bridge)return;bridge.openConversation(id,raw=>{let d={};try{d=JSON.parse(raw)}catch{};if(!d.ok)return;
    $('conversation').innerHTML='';(d.messages||[]).forEach(m=>addMessage(m.role==='assistant'?'assistant':'user',m.content,!m?.metadata?.error,(m.created_at||'').slice(11,16)));
    if(!(d.messages||[]).length)showWelcome();fetchSnapshot();
  });
}
function showWelcome(){
  $('conversation').innerHTML=`<div class="welcome" id="welcome"><div class="welcome-orb">✦</div><h1>O que você precisa?</h1><p>Converse normalmente. O Jarvis decide quando lembrar, pesquisar, consultar dados públicos ou agir.</p><div class="welcome-hints"><button data-prompt="Pesquise fontes oficiais sobre um assunto que eu indicar.">Pesquisar</button><button data-prompt="O que você lembra das nossas conversas recentes?">Lembrar</button><button data-prompt="Analise o que está em andamento e me diga o que merece atenção.">Analisar</button></div></div>`;
  bindPromptButtons();
}
function renderContext(){
  const active=snapshot?.active_task;const conv=snapshot?.cognitive?.conversations||{};const learning=snapshot?.cognitive?.learning||{};const kb=snapshot?.knowledge||{};
  $('taskCard').innerHTML=active?`<strong>${esc(active.goal||'Tarefa ativa')}</strong><span>${esc(active.status||'running')}</span>`:`<strong>Nenhuma tarefa ativa</strong><span>O Jarvis está disponível para conversar ou agir.</span>`;
  $('cognitiveStats').innerHTML=`<div class="mini"><small>CONVERSAS</small><b>${conv.sessions||0}</b></div><div class="mini"><small>MENSAGENS</small><b>${conv.messages||0}</b></div><div class="mini"><small>LIÇÕES</small><b>${learning.active_lessons||0}</b></div><div class="mini"><small>KNOWLEDGE</small><b>${kb.documents||0}</b></div>`;
  const lessons=snapshot?.cognitive?.lessons||[];$('lessonList').innerHTML=lessons.slice(0,8).map(x=>`<div class="simple-item"><b>${esc(x.kind||'lesson')}</b><span>${esc(x.lesson||'')}</span></div>`).join('')||'<div class="simple-item"><span>Nenhuma preferência/correção aprendida ainda.</span></div>';
}
function renderSources(){
  const pd=snapshot?.public_data||{};const stats=pd.stats||{};const sources=pd.sources||[];
  $('sourceStats').innerHTML=`<span class="pill">${stats.sources||0} fontes</span><span class="pill">${stats.official||0} oficiais</span>`;
  $('sourceList').innerHTML=sources.slice(0,14).map(x=>`<div class="simple-item"><b>${esc(x.name)}</b><span>${esc((x.topics||[]).slice(0,4).join(' • '))}</span></div>`).join('');
}
function renderActivity(){
  const tasks=snapshot?.recent_tasks||[];const alerts=snapshot?.notifications?.unread||[];
  $('activityList').innerHTML=tasks.slice(0,8).map(x=>`<div class="simple-item"><b>#${x.id} • ${esc((x.status||'').toUpperCase())}</b><span>${esc(x.goal||'')}</span></div>`).join('')||'<div class="simple-item"><span>Nenhuma atividade recente.</span></div>';
  $('alertList').innerHTML=alerts.slice(0,8).map(x=>`<div class="simple-item"><b>${esc(x.title||'Alerta')}</b><span>${esc(x.message||'')}</span></div>`).join('')||'<div class="simple-item"><span>Nenhum alerta pendente.</span></div>';
}
function renderControlCenter(){
  if(!snapshot)return;const a=snapshot.actions||{},w=snapshot.workflows||{},c=snapshot.capabilities||{},p=snapshot.public_data?.stats||{},k=snapshot.knowledge||{},b=snapshot.browser||{},auto=snapshot.automations?.stats||{},con=snapshot.connectors?.stats||{};
  const tiles=[['COGNITIVE',(snapshot.cognitive?.conversations?.messages||0),'mensagens persistentes'],['KNOWLEDGE',k.documents||0,'documentos indexados'],['PUBLIC DATA',p.sources||0,'fontes catalogadas'],['CAPABILITIES',c.capabilities||0,'dados/serviços públicos'],['ACTIONS',a.actions||0,'infraestrutura interna'],['WORKFLOWS',w.workflows||0,'fluxos compostos'],['BACKGROUND',auto.jobs||0,'automações'],['CONNECTORS',con.connectors||0,'integrações configuradas']];
  $('controlGrid').innerHTML=tiles.map(x=>`<div class="control-tile"><small>${x[0]}</small><b>${x[1]}</b><span>${x[2]}</span></div>`).join('');
}
function searchSources(){
  const q=$('sourceQuery').value.trim();if(!q||!bridge)return;$('sourceSearchResults').innerHTML='<div class="advanced-note">Pesquisando catálogo…</div>';
  bridge.searchPublicSources(q,raw=>{let d={};try{d=JSON.parse(raw)}catch{};const items=d.items||[];$('sourceSearchResults').innerHTML=items.map(x=>`<div class="source-card"><b>${esc(x.name)}</b><span>${esc(x.access||'')} • ${esc(x.authority||'')}</span><span>${esc((x.topics||[]).slice(0,5).join(' • '))}</span></div>`).join('')||'<div class="advanced-note">Nenhuma fonte correspondente.</div>';});
}
function bindPromptButtons(){document.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>sendPrompt(b.dataset.prompt))}
function setInspectorTab(name){document.querySelectorAll('.inspector-tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('active',p.id===`panel-${name}`))}

function initBridge(){
  if(typeof QWebChannel==='undefined'||typeof qt==='undefined'){setTimeout(initBridge,250);return}
  new QWebChannel(qt.webChannelTransport,channel=>{
    bridge=channel.objects.jarvisBridge;
    bridge.statusChanged.connect((state,detail)=>{setBusy(true,detail||state);showThinking(detail||state)});
    bridge.commandFinished.connect((prompt,result,ok)=>{removeThinking();addMessage('assistant',result,ok);setBusy(false);fetchSnapshot()});
    bridge.snapshotChanged.connect(raw=>{try{renderSnapshot(JSON.parse(raw))}catch(e){console.error(e)}});
    fetchSnapshot();
  });
}

$('sendBtn').onclick=()=>sendPrompt($('promptInput').value);
$('promptInput').addEventListener('input',resizeInput);
$('promptInput').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendPrompt(e.target.value)}});
$('cancelBtn').onclick=()=>bridge&&bridge.cancelTask();
$('newChatBtn').onclick=()=>{if(bridge)bridge.newChat();showWelcome();fetchSnapshot()};
$('controlBtn').onclick=()=>{$('controlOverlay').classList.remove('hidden');renderControlCenter()};
$('closeControl').onclick=()=>$('controlOverlay').classList.add('hidden');
$('controlOverlay').onclick=e=>{if(e.target===$('controlOverlay'))$('controlOverlay').classList.add('hidden')};
$('sourceSearchBtn').onclick=searchSources;$('sourceQuery').addEventListener('keydown',e=>{if(e.key==='Enter')searchSources()});
$('contextToggle').onclick=()=>$('inspector').classList.toggle('hidden');$('closeInspector').onclick=()=>$('inspector').classList.add('hidden');
$('compactBtn').onclick=()=>{document.body.classList.toggle('compact');if(bridge)bridge.setMode(document.body.classList.contains('compact')?'compact':'habitat')};
document.querySelectorAll('[data-window]').forEach(b=>b.onclick=()=>bridge&&bridge.windowAction(b.dataset.window));
document.querySelectorAll('.inspector-tab').forEach(b=>b.onclick=()=>setInspectorTab(b.dataset.tab));
bindPromptButtons();initBridge();
