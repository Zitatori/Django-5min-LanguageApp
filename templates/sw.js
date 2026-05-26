const CACHE_NAME = 'quicklesson-v1';

// インストール時: 最低限のアセットをキャッシュ
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache =>
      cache.addAll(['/', '/static/css/style.css'])
    )
  );
  self.skipWaiting();
});

// 古いキャッシュを削除
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// ネットワーク優先 → 失敗したらキャッシュを返す
self.addEventListener('fetch', event => {
  // WebSocket・API・動画ストリームはキャッシュしない
  if (
    event.request.url.includes('/ws/') ||
    event.request.method !== 'GET'
  ) return;

  event.respondWith(
    fetch(event.request)
      .then(response => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
