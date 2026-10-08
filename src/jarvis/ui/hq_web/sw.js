const CACHE='jarvis-shell-v12.2';
const SHELL=['/','/mobile','/companion.css?v=12.2','/companion.js?v=12.2','/mobile.css?v=12.2','/mobile.js?v=12.2','/jarvis-core.js?v=12.2','/surface-engine.js?v=12.2','/morning-sequence.css?v=12.2','/morning-sequence.js?v=12.2','/jarvis-icon.svg','/manifest.webmanifest','/mobile.webmanifest'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
  const req=event.request,u=new URL(req.url);
  if(req.method!=='GET'||u.pathname.startsWith('/api/'))return;
  const critical=/\.(?:css|js)$/i.test(u.pathname)||u.pathname==='/'||u.pathname==='/mobile';
  if(critical){
    event.respondWith(fetch(req,{cache:'no-cache'}).then(r=>{if(r.ok){const copy=r.clone();caches.open(CACHE).then(c=>c.put(req,copy));}return r}).catch(()=>caches.match(req)));
    return;
  }
  const asset=/\.(?:svg|png|webp|woff2?|webmanifest)$/i.test(u.pathname);
  if(asset){
    event.respondWith(caches.match(req).then(cached=>cached||fetch(req).then(r=>{if(r.ok){const copy=r.clone();caches.open(CACHE).then(c=>c.put(req,copy));}return r})));
    return;
  }
  event.respondWith(fetch(req,{cache:'no-cache'}).then(r=>{if(r.ok){const copy=r.clone();caches.open(CACHE).then(c=>c.put(req,copy));}return r}).catch(()=>caches.match(req)));
});
