// 离线优先，升级兼容：新版本修改 CACHE 版本号，且 HTML 页面在线时总是先尝试获取新版。
const CACHE='sv-tactical-iphone-v0.3.0';
const ASSETS=['./','./index.html','./icon.svg','./apple-touch-icon.png','./manifest.webmanifest','./version.json'];
self.addEventListener('install',event=>{
  event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',event=>{
  event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('sv-tactical-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET')return;
  const url=new URL(event.request.url);
  const scope=new URL(self.registration.scope);
  if(url.origin!==scope.origin||!url.pathname.startsWith(scope.pathname))return;
  const navigation=event.request.mode==='navigate';
  const checkVersion=url.pathname.endsWith('/version.json');
  if(navigation||checkVersion){
    // 在线时尽量获取最新版本；断网时使用已缓存页面。
    event.respondWith(fetch(event.request).then(response=>{
      if(response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(navigation?'./index.html':'./version.json',copy)).catch(()=>{});}
      return response;
    }).catch(async()=> (await caches.match(event.request,{ignoreSearch:true}))||(navigation?(await caches.match('./index.html')):null)||Response.error()));
    return;
  }
  // 仅缓存应用清单内的同源文件，防止无意义的缓存膨胀。
  const matched=ASSETS.some(entry=>new URL(entry,scope).pathname===url.pathname);
  if(matched)event.respondWith(caches.match(event.request,{ignoreSearch:true}).then(hit=>hit||fetch(event.request).then(response=>{
    if(response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy)).catch(()=>{});}
    return response;
  })));
});
