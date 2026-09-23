const $=id=>document.getElementById(id);let token=localStorage.getItem('jarvisMobileToken')||'';let snapshot=null;let busy=false;
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
function md(t){let x=esc(String(t||''));x=x.replace(/```([\s\S]*?)```/g,'<pre><code>$1</code></pre>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,'<a href="$2" target="_blank">$1</a>').replace(/\n/g,'<br>');return x}
async function api(path,opt={}){opt.headers={...(opt.headers||{}),'Content-Type':'application/json',...(token?{'Authorization':'Bearer '+token}:{})};const r=await fetch(path,opt);let d={};try{d=await r.json()}catch{};if(r.status===401&&path!='/api/pair'){token='';localStorage.removeItem('jarvisMobileToken');showPair()}return d}
function showPair(){ $('pairScreen').classList.remove('hidden');$('app').classList.add('hidden') }
function showApp(){ $('pairScreen').classList.add('hidden');$('app').classList.remove('hidden') }
async function pair(){const pin=$('pinInput').value.trim();$('pairError').textContent='';if(pin.length!==6){$('pairError').textContent='Digite o PIN de 6 dígitos.';return}const d=await api('/api/pair',{method:'POST',body:JSON.stringify({pin})});if(!d.ok){$('pairError').textContent=d.error||'Não foi possível conectar.';return}token=d.token;localStorage.setItem('jarvisMobileToken',token);showApp();await refresh();await loadHistory()}
function addMessage(role,text,meta={}){const welcome=$('welcome');if(welcome)welcome.style.display='none';const el=document.createElement('div');el.className=`message ${role}`;const sources=Array.isArray(meta.sources)?meta.sources:[];el.innerHTML=`<div class="avatar">${role==='user'?'V':'✦'}</div><div><div class="message-head">${role==='user'?'Você':'Jarvis'}${meta.model?`<small>${esc(meta.model)}</small>`:''}</div><div class="message-body">${role==='assistant'?md(text):esc(text).replace(/\n/g,'<br>')}</div>${sources.length?`<div class="message-sources">${sources.slice(0,4).map(s=>s.url?`<a href="${esc(s.url)}" target="_blank">${esc(s.title||s.name||'Fonte')}</a>`:'').join('')}</div>`:''}</div>`;$('chat').appendChild(el);$('chat').scrollTop=$('chat').scrollHeight}
function thinking(text='Jarvis está trabalhando…'){removeThinking();const el=document.createElement('div');el.id='thinking';el.className='thinking';el.textContent=text;$('chat').appendChild(el);$('chat').scrollTop=$('chat').scrollHeight}
function removeThinking(){const el=$('thinking');if(el)el.remove()}
function resize(){const el=$('messageInput');el.style.height='auto';el.style.height=Math.min(130,el.scrollHeight)+'px'}
async function send(value){const msg=String(value||'').trim();if(!msg||busy)return;busy=true;addMessage('user',msg);$('messageInput').value='';resize();thinking('Jarvis está pensando no computador…');$('statusLabel').textContent='local • trabalhando';const d=await api('/api/chat',{method:'POST',body:JSON.stringify({message:msg})});removeThinking();busy=false;$('statusLabel').textContent='local • pronto';if(d.ok)addMessage('assistant',d.answer,d.metadata||{});else addMessage('assistant',d.error||'Não foi possível concluir.');await refresh()}
async function refresh(){const d=await api('/api/snapshot');if(!d.ok)return;snapshot=d;renderSnapshot()}
function renderSnapshot(){const p=snapshot.project;const conv=snapshot.conversations?.items||[];$('projectCard').innerHTML=p?`<b>${esc(p.name)}</b><span>${esc(p.description||'Projeto atual')}</span>`:'<b>Sem projeto ativo</b><span>Conversa geral</span>';$('metricGrid').innerHTML=`<div class="metric"><small>CONVERSAS</small><b>${conv.length}</b></div><div class="metric"><small>PERFIL</small><b>${esc(snapshot.hardware?.tier||'local')}</b></div><div class="metric"><small>FAST</small><b>${esc((snapshot.model?.fast||'—').replace('qwen3:',''))}</b></div><div class="metric"><small>REASON</small><b>${esc((snapshot.model?.reason||'—').replace('qwen3:',''))}</b></div>`;$('conversationList').innerHTML=conv.map(c=>`<button class="conversation-item ${Number(c.id)===Number(snapshot.current_session)?'active':''}" data-session="${c.id}">${esc(c.title||'Conversa')}</button>`).join('');document.querySelectorAll('[data-session]').forEach(b=>b.onclick=()=>selectConversation(Number(b.dataset.session)))}
async function loadHistory(session=null){const d=await api(`/api/history${session?`?session=${session}`:''}`);if(!d.ok)return;$('chat').innerHTML='';(d.messages||[]).forEach(m=>{let meta=m.metadata||{};if(typeof meta==='string'){try{meta=JSON.parse(meta)}catch{meta={}}}addMessage(m.role==='assistant'?'assistant':'user',m.content,meta)});if(!(d.messages||[]).length){$('chat').innerHTML='<section class="welcome" id="welcome"><div class="hero-orb"><span>✦</span></div><h2>Nova conversa.</h2><p>Fale normalmente com o Jarvis.</p></section>'}}
async function selectConversation(id){await api('/api/conversation/select',{method:'POST',body:JSON.stringify({session_id:id})});closeSheets();await refresh();await loadHistory(id)}
async function newChat(){await api('/api/conversation/new',{method:'POST',body:'{}'});closeSheets();await refresh();await loadHistory()}
function openSheet(id){$(id).classList.remove('hidden')}function closeSheets(){document.querySelectorAll('.sheet').forEach(s=>s.classList.add('hidden'))}
async function uploadFile(file){if(!file)return;if(file.size>15*1024*1024){alert('Limite mobile: 15 MB.');return}const chip=document.createElement('div');chip.className='upload-chip';chip.textContent=`Enviando ${file.name}…`;$('uploadStrip').appendChild(chip);const data=await new Promise((res,rej)=>{const r=new FileReader();r.onload=()=>res(String(r.result).split(',')[1]);r.onerror=rej;r.readAsDataURL(file)});const d=await api('/api/upload',{method:'POST',body:JSON.stringify({name:file.name,data})});chip.textContent=d.ok?`${file.name} anexado`:`Falha: ${file.name}`;setTimeout(()=>chip.remove(),3000)}
function pinFromLocation(){
  const q=new URLSearchParams(location.search).get('pin')||'';
  const path=(location.pathname||'').replace(/^\/+|\/+$/g,'');
  const hash=(location.hash||'').replace(/^#/,'');
  for(const value of [q,path,hash]){
    if(/^\d{6}$/.test(value))return value;
  }
  return '';
}
async function boot(){
  const locationPin=pinFromLocation();
  if(locationPin){
    // Remove PIN from browser history/address bar before authenticating.
    history.replaceState({},'', '/');
    $('pinInput').value=locationPin;
  }
  const st=await api('/api/status');
  if(st.paired||token){
    showApp();await refresh();await loadHistory();return;
  }
  showPair();
  if(locationPin)await pair();
}
$('pairBtn').onclick=pair;$('pinInput').addEventListener('keydown',e=>{if(e.key==='Enter')pair()});$('sendBtn').onclick=()=>send($('messageInput').value);$('messageInput').addEventListener('input',resize);$('messageInput').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send(e.target.value)}});$('historyBtn').onclick=()=>openSheet('historySheet');$('contextBtn').onclick=()=>openSheet('contextSheet');document.querySelectorAll('[data-close-sheet]').forEach(x=>x.onclick=closeSheets);$('newChatBtn').onclick=newChat;$('attachBtn').onclick=()=>$('fileInput').click();$('fileInput').onchange=e=>{const f=e.target.files?.[0];if(f)uploadFile(f);e.target.value=''};document.querySelectorAll('[data-prompt]').forEach(x=>x.onclick=()=>send(x.dataset.prompt));boot();
