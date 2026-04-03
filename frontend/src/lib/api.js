const BASE = '/api'

async function get(path) {
  const resp = await fetch(`${BASE}${path}`)
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}))
    throw new Error(body.error || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export function fetchTrending(page = 1, type = 'all') {
  return get(`/trending?type=${type}&window=week&page=${page}`)
}

export function fetchPopular(type = 'movie', page = 1) {
  return get(`/popular?type=${type}&page=${page}`)
}

export function fetchDiscover(type, genreId, page = 1) {
  return get(`/discover?type=${type}&genre=${genreId}&page=${page}`)
}

export function fetchSearch(query, page = 1) {
  return get(`/search?q=${encodeURIComponent(query)}&page=${page}`)
}

export function fetchDetail(type, id) {
  return get(`/detail?type=${type}&id=${id}`)
}

export function fetchProviders(type, id, region = 'US') {
  return get(`/providers?type=${type}&id=${id}&region=${region}`)
}

export async function addMagnet(magnet, savepath = '', category = '') {
  const resp = await fetch(`${BASE}/qbt/add`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ magnet, savepath: savepath || undefined, category: category || undefined }),
  })
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}))
    throw new Error(body.error || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export function fetchTorrents() {
  return get('/qbt/torrents')
}

export async function markWatchedByHashes(hashes) {
  const resp = await fetch(`${BASE}/qbt/mark-watched`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hashes }),
  })
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}))
    throw new Error(body.error || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export async function deleteTorrents(hashes, deleteFiles = false) {
  const resp = await fetch(`${BASE}/qbt/delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hashes, delete_files: deleteFiles }),
  })
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}))
    throw new Error(body.error || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export function fetchFolders(base = 'tv') {
  return get(`/qbt/folders?base=${base}`)
}

export async function recordDownload(data) {
  const resp = await fetch(`${BASE}/downloads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}))
    throw new Error(body.error || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export function fetchShowFolder(tmdbId) {
  return get(`/tv/${tmdbId}/show-folder`)
}

export function fetchTvSeasons(tmdbId) {
  return get(`/tv/${tmdbId}/seasons`)
}

export function fetchTvEpisodes(tmdbId, seasonNumber) {
  return get(`/tv/${tmdbId}/season/${seasonNumber}`)
}

export function searchTorrents(query) {
  return get(`/torrent/search?q=${encodeURIComponent(query)}`)
}

export function fetchFileSize(path) {
  return get(`/files/size?path=${encodeURIComponent(path)}`)
}

export function fetchDiskUsage() {
  return get('/files/disk')
}

export function downloadFile(path) {
  const a = document.createElement('a')
  a.href = `${BASE}/files/download?path=${encodeURIComponent(path)}`
  a.download = ''
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

export function listFiles(path) {
  return get(`/files/list?path=${encodeURIComponent(path)}`)
}

export async function deleteFiles(paths) {
  const resp = await fetch(`${BASE}/files/delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paths }),
  })
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}))
    throw new Error(body.error || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export async function renameFile(path, new_name) {
  const resp = await fetch(`${BASE}/files/rename`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, new_name }),
  })
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}))
    throw new Error(body.error || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export async function moveFiles(paths, dest_dir) {
  const resp = await fetch(`${BASE}/files/move`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paths, dest_dir }),
  })
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}))
    throw new Error(body.error || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export async function markItem(tmdbId, mediaType, title, posterUrl, flag, value = true) {
  const resp = await fetch(`${BASE}/items/mark`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tmdb_id: tmdbId, media_type: mediaType, title, poster_url: posterUrl, flag, value }),
  })
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}))
    throw new Error(body.error || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export function fetchItemsByFlag(flag) {
  return get(`/items?flag=${flag}`)
}

export async function fetchItemStates(items) {
  // items: [{tmdb_id, media_type}, ...]
  const resp = await fetch(`${BASE}/items/states`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  })
  if (!resp.ok) return {}
  return resp.json()
}
