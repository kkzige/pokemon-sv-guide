/* Production PWA worker v1.2.2. Install via original HTTPS origin only. */
const CACHE='pokemon-sv-guide-v1.2.2';
const CORE=['./','./index.html','./manifest.webmanifest','./icon.svg','./apple-touch-icon.png','./sv-data.json'];
self.addEventListener('install',event=>{event.waitUntil((async()=>{const cache=await caches.open(CACHE);for(const url of CORE){try{const res=await fetch(new Request(url,{cache:'reload'}));if(res.ok)await cache.put(url,res.clone());}catch{}}await self.skipWaiting();})());});
self.addEventListener('activate',event=>{event.waitUntil((async()=>{const keys=await caches.keys();await Promise.all(keys.filter(k=>k.startsWith('pokemon-sv-guide-')&&k!==CACHE).map(k=>caches.delete(k)));await self.clients.claim();})());});
self.addEventListener('fetch',event=>{const req=event.request;if(req.method!=='GET')return;const url=new URL(req.url);if(url.origin!==self.location.origin)return;const isPage=req.mode==='navigate'||url.pathname.endsWith('/index.html')||url.pathname.endsWith('/version.json');event.respondWith((async()=>{const cache=await caches.open(CACHE);if(isPage){try{const res=await fetch(req,{cache:'no-cache'});if(res.ok)await cache.put(req,res.clone());return res;}catch{return await cache.match(req)||await cache.match('./index.html')||Response.error();}}const cached=await cache.match(req);if(cached)return cached;try{const res=await fetch(req);if(res.ok)await cache.put(req,res.clone());return res;}catch{return Response.error();}})());});

// Keep original behavior: two sets of 18 official-type icons can be pre-cached.
const ICON_HOSTS=new Set(['raw.githubusercontent.com','cdn.jsdelivr.net']);
const TYPE_PATH='sprites/types/generation-ix/scarlet-violet/small/';
const TERA_PATH=TYPE_PATH+'Tera/';
function iconUrl(n,tera){return 'https://raw.githubusercontent.com/PokeAPI/sprites/master/'+(tera?TERA_PATH:TYPE_PATH)+n+'.png';}
async function countAndCacheIcons(tera){
 const cache=await caches.open(CACHE);let count=0;
 for(let n=1;n<=18;n++){
  const url=iconUrl(n,tera);
  try{
   let res=await cache.match(url);
   if(!res){res=await fetch(url,{mode:'cors'});if(res.ok)await cache.put(url,res.clone());}
   if(res?.ok)count++;
  }catch{}
 }
 return count;
}
self.addEventListener('message',event=>{
 const tera=event.data?.type==='CACHE_TERA_ICONS',types=event.data?.type==='CACHE_SV_TYPE_ICONS';
 if(!tera&&!types)return;
 const task=(async()=>{const count=await countAndCacheIcons(tera);event.source?.postMessage({type:tera?'TERA_CACHE_COUNT':'SV_TYPE_CACHE_COUNT',count});})();
 event.waitUntil(task);
});
// Cross-origin source images are only cached for the known public Pokémon type icon paths.
self.addEventListener('fetch',event=>{
 const req=event.request;if(req.method!=='GET')return;let url;
 try{url=new URL(req.url);}catch{return;}
 if(!ICON_HOSTS.has(url.hostname))return;
 if(!url.pathname.includes(TYPE_PATH)&&!url.pathname.includes('/'+TYPE_PATH))return;
 event.respondWith((async()=>{const cache=await caches.open(CACHE);const hit=await cache.match(req);if(hit)return hit;try{const res=await fetch(req);if(res.ok)await cache.put(req,res.clone());return res;}catch{return Response.error();}})());
});
