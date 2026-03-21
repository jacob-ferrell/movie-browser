<script>
  import { addMagnet, fetchTorrents } from './api.js'

  let magnet = $state('')
  let mediaType = $state('movie') // 'movie' | 'tv'
  let folderName = $state('')
  let adding = $state(false)
  let addError = $state(null)
  let addSuccess = $state(false)

  const BASE_PATHS = { movie: '/hdd/Movies', tv: '/hdd/tvshows' }

  function parseDn(magnetLink) {
    try {
      const match = magnetLink.match(/[?&]dn=([^&]+)/)
      if (match) return decodeURIComponent(match[1].replace(/\+/g, ' '))
    } catch {}
    return ''
  }

  // Extracts a clean "Title.Name.Year" from a raw torrent display name.
  // Strips quality tags ([1080p], [WEBRip], [5.1], etc.) and everything after the year.
  function extractTitle(raw) {
    let s = raw
      // Remove bracket groups entirely: [1080p], [WEBRip], [5.1], [AAC], etc.
      .replace(/\[.*?\]/g, ' ')
      // Unwrap parentheses: (2024) → "2024", anything else → space
      .replace(/\(([^)]*)\)/g, (_, inner) =>
        /^(?:19|20)\d{2}$/.test(inner.trim()) ? ` ${inner.trim()} ` : ' '
      )

    const yearMatch = s.match(/\b((?:19|20)\d{2})\b/)

    if (yearMatch) {
      const titlePart = s
        .slice(0, yearMatch.index)
        .replace(/[^a-zA-Z0-9\s]/g, ' ') // dots, dashes → spaces
        .trim()
        .replace(/\s+/g, '.')
      return titlePart ? `${titlePart}.${yearMatch[1]}` : yearMatch[1]
    }

    // No year — just clean up whatever we have
    return s.replace(/[^a-zA-Z0-9\s]/g, ' ').trim().replace(/\s+/g, '.')
  }

  // Light sanitization of user-typed folder name for use as a directory name
  function normalize(name) {
    return name
      .trim()
      .replace(/[<>:"/\\|?*]/g, '')
      .replace(/\s+/g, '.')
      .replace(/\.{2,}/g, '.')
      .replace(/^\.+|\.+$/g, '')
  }

  let computedPath = $derived(
    folderName.trim()
      ? `${BASE_PATHS[mediaType]}/${normalize(folderName)}`
      : BASE_PATHS[mediaType]
  )

  $effect(() => {
    const dn = parseDn(magnet)
    if (dn) folderName = extractTitle(dn)
  })

  let torrents = $state([])
  let listError = $state(null)

  const STATE_LABELS = {
    downloading: { label: 'Downloading', color: 'bg-teal-600/20 text-teal-400' },
    uploading:   { label: 'Seeding',     color: 'bg-green-600/20 text-green-400' },
    seeding:     { label: 'Seeding',     color: 'bg-green-600/20 text-green-400' },
    pausedDL:    { label: 'Paused',      color: 'bg-gray-600/20 text-gray-400' },
    pausedUP:    { label: 'Paused',      color: 'bg-gray-600/20 text-gray-400' },
    stalledDL:   { label: 'Stalled',     color: 'bg-amber-600/20 text-amber-400' },
    stalledUP:   { label: 'Stalled',     color: 'bg-amber-600/20 text-amber-400' },
    queuedDL:    { label: 'Queued',      color: 'bg-amber-600/20 text-amber-400' },
    queuedUP:    { label: 'Queued',      color: 'bg-amber-600/20 text-amber-400' },
    error:       { label: 'Error',       color: 'bg-red-600/20 text-red-400' },
    missingFiles:{ label: 'Missing',     color: 'bg-red-600/20 text-red-400' },
    checkingDL:  { label: 'Checking',    color: 'bg-blue-600/20 text-blue-400' },
    checkingUP:  { label: 'Checking',    color: 'bg-blue-600/20 text-blue-400' },
    moving:      { label: 'Moving',      color: 'bg-blue-600/20 text-blue-400' },
  }

  function stateInfo(state) {
    return STATE_LABELS[state] ?? { label: state, color: 'bg-gray-700 text-gray-400' }
  }

  function fmtSize(bytes) {
    if (!bytes) return '—'
    if (bytes >= 1e9) return (bytes / 1e9).toFixed(1) + ' GB'
    if (bytes >= 1e6) return (bytes / 1e6).toFixed(1) + ' MB'
    return (bytes / 1e3).toFixed(0) + ' KB'
  }

  function fmtSpeed(bps) {
    if (!bps) return ''
    if (bps >= 1e6) return (bps / 1e6).toFixed(1) + ' MB/s'
    return (bps / 1e3).toFixed(0) + ' KB/s'
  }

  function fmtEta(secs) {
    if (!secs || secs >= 8640000) return ''
    if (secs >= 3600) return `${Math.floor(secs / 3600)}h ${Math.floor((secs % 3600) / 60)}m`
    if (secs >= 60) return `${Math.floor(secs / 60)}m ${secs % 60}s`
    return `${secs}s`
  }

  async function load() {
    try {
      torrents = await fetchTorrents()
      listError = null
    } catch (e) {
      listError = e.message
    }
  }

  async function handleAdd() {
    if (!magnet.trim()) return
    adding = true
    addError = null
    addSuccess = false
    try {
      await addMagnet(magnet.trim(), computedPath)
      magnet = ''
      folderName = ''
      addSuccess = true
      setTimeout(() => addSuccess = false, 3000)
      await load()
    } catch (e) {
      addError = e.message
    } finally {
      adding = false
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') handleAdd()
  }

  $effect(() => {
    load()
    const id = setInterval(load, 3000)
    return () => clearInterval(id)
  })
</script>

<div class="max-w-4xl mx-auto py-6 flex flex-col gap-6">
  <!-- Add magnet section -->
  <div class="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-4">
    <h2 class="text-base font-semibold text-gray-100">Add Torrent</h2>

    <!-- Magnet input -->
    <input
      type="text"
      placeholder="magnet:?xt=urn:btih:..."
      bind:value={magnet}
      onkeydown={handleKeydown}
      class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-teal-500 font-mono"
    />

    <!-- Media type toggle -->
    <div class="flex gap-2">
      {#each [['movie', 'Movie', '/hdd/Movies'], ['tv', 'TV Show', '/hdd/tvshows']] as [val, label, path]}
        <label class="flex items-center gap-2 cursor-pointer flex-1 bg-gray-800 border rounded-lg px-3 py-2.5 transition {mediaType === val ? 'border-teal-500 text-teal-300' : 'border-gray-700 text-gray-400 hover:border-gray-600'}">
          <input type="radio" bind:group={mediaType} value={val} class="accent-teal-500" />
          <span class="text-sm font-medium">{label}</span>
          <span class="text-xs text-gray-600 ml-auto font-mono">{path}/</span>
        </label>
      {/each}
    </div>

    <!-- Folder name -->
    <div class="flex flex-col gap-1.5">
      <label class="text-xs text-gray-500 font-medium">Folder name</label>
      <input
        type="text"
        placeholder="My.Movie.Name.2026"
        bind:value={folderName}
        onkeydown={handleKeydown}
        class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-teal-500 font-mono"
      />
      <p class="text-xs font-mono text-gray-600 truncate" title={computedPath}>
        → {computedPath}{normalize(folderName) ? '' : '<folder>'}
      </p>
    </div>

    <button
      onclick={handleAdd}
      disabled={adding || !magnet.trim()}
      class="self-start px-5 py-2 bg-teal-600 hover:bg-teal-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-sm font-medium text-white transition"
    >
      {adding ? 'Adding…' : 'Add Torrent'}
    </button>

    {#if addError}
      <p class="text-red-400 text-xs">{addError}</p>
    {/if}
    {#if addSuccess}
      <p class="text-teal-400 text-xs">Torrent added successfully.</p>
    {/if}
  </div>

  <!-- Torrent list -->
  <div class="flex flex-col gap-2">
    <div class="flex items-center justify-between">
      <h2 class="text-base font-semibold text-gray-100">Downloads</h2>
      {#if torrents.length > 0}
        <span class="text-xs text-gray-500">{torrents.length} torrent{torrents.length !== 1 ? 's' : ''}</span>
      {/if}
    </div>

    {#if listError}
      <div class="bg-red-900/20 border border-red-800 rounded-xl p-4 text-red-400 text-sm">
        Could not connect to qBittorrent: {listError}
      </div>
    {:else if torrents.length === 0}
      <div class="bg-gray-900 border border-gray-800 rounded-xl p-10 text-center text-gray-600 text-sm">
        No torrents yet. Add a magnet link above.
      </div>
    {:else}
      {#each torrents as t (t.hash)}
        {@const si = stateInfo(t.state)}
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col gap-2">
          <div class="flex items-start justify-between gap-3">
            <p class="text-sm text-gray-100 font-medium leading-snug flex-1 min-w-0 truncate" title={t.name}>
              {t.name}
            </p>
            <span class="shrink-0 text-[11px] font-semibold px-2 py-0.5 rounded-full {si.color}">
              {si.label}
            </span>
          </div>

          <!-- Progress bar -->
          <div class="w-full bg-gray-700 rounded-full h-1.5 overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-500 {t.progress >= 1 ? 'bg-green-500' : 'bg-teal-500'}"
              style="width: {(t.progress * 100).toFixed(1)}%"
            ></div>
          </div>

          <!-- Stats row -->
          <div class="flex items-center gap-4 text-xs text-gray-500 flex-wrap">
            <span>{(t.progress * 100).toFixed(1)}%</span>
            <span>{fmtSize(t.size)}</span>
            {#if t.dlspeed > 0}
              <span class="text-teal-500">↓ {fmtSpeed(t.dlspeed)}</span>
            {/if}
            {#if t.upspeed > 0}
              <span class="text-green-500">↑ {fmtSpeed(t.upspeed)}</span>
            {/if}
            {#if fmtEta(t.eta)}
              <span>ETA {fmtEta(t.eta)}</span>
            {/if}
            {#if t.category}
              <span class="bg-gray-800 px-1.5 py-0.5 rounded text-gray-400">{t.category}</span>
            {/if}
          </div>
        </div>
      {/each}
    {/if}
  </div>
</div>
