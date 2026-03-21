<script>
  import { searchTorrents, addMagnet, fetchFolders, recordDownload, fetchShowFolder } from './api.js'
  import { setFlag } from './itemStates.svelte.js'

  let {
    title, mediaType = 'movie', tmdbId = null, posterUrl = null, onBack,
    seasonNumber = null, episodeNumber = null, episodeName = null,
  } = $props()

  let results = $state([])
  let loading = $state(true)
  let error = $state(null)

  // Per-result add state: keyed by result id
  let adding = $state({})     // id → true/false
  let addDone = $state({})    // id → true/false
  let addError = $state({})   // id → error string

  // Inline confirm panel open state
  let confirming = $state(null) // id of result being confirmed, or null

  // Per-result folder name (editable)
  let folderNames = $state({})

  const BASE_PATHS = { movie: '/hdd/Movies', tv: '/hdd/tvshows' }
  let selectedType = $state(mediaType)

  // TV: shared show-level parent folder (same show for all results on this page)
  let tvShowFolder = $state(normalizeShowTitle(title))
  let existingTvFolders = $state([])

  function normalizeShowTitle(t) {
    return (t || '').replace(/\s*S\d{2}E\d{2}.*/i, '').trim()
      .replace(/[<>:"/\\|?*]/g, '').replace(/\s+/g, '.')
  }

  $effect(() => {
    if (selectedType === 'tv') {
      fetchFolders('tv').then(f => { existingTvFolders = f }).catch(() => {})
      // If this show has been downloaded before, use the stored folder name
      if (tmdbId) {
        fetchShowFolder(tmdbId).then(data => {
          if (data.folder) tvShowFolder = data.folder
        }).catch(() => {})
      }
    }
  })

  function computePath(id) {
    const base = BASE_PATHS[selectedType]
    if (selectedType === 'tv') {
      const show = tvShowFolder.trim().replace(/\.{2,}/g, '.').replace(/^\.+|\.+$/g, '')
      const ep = normalize(folderNames[id] || '')
      if (show && ep) return `${base}/${show}/${ep}`
      if (show) return `${base}/${show}`
      return base
    }
    const folder = normalize(folderNames[id] || '')
    return folder ? `${base}/${folder}` : base
  }

  function extractTitle(raw) {
    let s = raw
      .replace(/\[.*?\]/g, ' ')
      .replace(/\(([^)]*)\)/g, (_, inner) =>
        /^(?:19|20)\d{2}$/.test(inner.trim()) ? ` ${inner.trim()} ` : ' '
      )
    const yearMatch = s.match(/\b((?:19|20)\d{2})\b/)
    if (yearMatch) {
      const titlePart = s.slice(0, yearMatch.index)
        .replace(/[^a-zA-Z0-9\s]/g, ' ').trim().replace(/\s+/g, '.')
      return titlePart ? `${titlePart}.${yearMatch[1]}` : yearMatch[1]
    }
    return s.replace(/[^a-zA-Z0-9\s]/g, ' ').trim().replace(/\s+/g, '.')
  }

  function extractEpisodeTitle(raw) {
    // Normalize separators and strip bracket content
    let s = raw.replace(/\[.*?\]/g, '').replace(/[\s.]+/g, '.')
    // Truncate after SxxExx (e.g. S04E02), keeping the code itself
    const epMatch = s.match(/S\d{2}E\d{2}/i)
    if (epMatch) {
      return s.slice(0, epMatch.index + epMatch[0].length)
        .replace(/\.{2,}/g, '.').replace(/^\.+|\.+$/g, '')
    }
    // Fall back to standard movie extractor
    return extractTitle(raw)
  }

  function normalize(name) {
    return name.trim()
      .replace(/[<>:"/\\|?*]/g, '')
      .replace(/\s+/g, '.')
      .replace(/\.{2,}/g, '.')
      .replace(/^\.+|\.+$/g, '')
  }

  function openConfirm(result) {
    confirming = result.id
    if (!folderNames[result.id]) {
      folderNames[result.id] = selectedType === 'tv'
        ? extractEpisodeTitle(result.title)
        : extractTitle(result.title)
    }
  }

  function extractHash(magnet) {
    const m = (magnet || '').match(/xt=urn:btih:([a-fA-F0-9]+)/i)
    return m ? m[1].toLowerCase() : null
  }

  async function handleAdd(result) {
    adding[result.id] = true
    addError[result.id] = null
    const savePath = computePath(result.id)
    try {
      await addMagnet(result.magnet, savePath)
      addDone[result.id] = true
      confirming = null
      if (tmdbId) {
        recordDownload({
          tmdb_id: tmdbId,
          media_type: selectedType,
          title,
          poster_url: posterUrl,
          save_path: savePath,
          torrent_name: result.title,
          torrent_hash: extractHash(result.magnet),
          season_number: seasonNumber,
          episode_number: episodeNumber,
          episode_name: episodeName,
        }).catch(() => {})
      }
    } catch (e) {
      addError[result.id] = e.message
    } finally {
      adding[result.id] = false
    }
  }

  function fmtSeeders(n) {
    const num = parseInt(n) || 0
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k'
    return String(num)
  }

  function seederColor(n) {
    const num = parseInt(n) || 0
    if (num >= 500) return 'text-emerald-400'
    if (num >= 100) return 'text-amber-400'
    if (num > 0)    return 'text-orange-400'
    return 'text-red-500'
  }

  $effect(() => {
    loading = true
    error = null
    searchTorrents(title)
      .then(data => { results = data; loading = false })
      .catch(e => { error = e.message; loading = false })
  })
</script>

<div class="max-w-5xl mx-auto py-6 flex flex-col gap-5">
  <!-- Header -->
  <div class="flex items-center gap-3">
    <button
      onclick={onBack}
      class="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-100 transition"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      Back
    </button>
    <div class="h-4 w-px bg-gray-700"></div>
    <h1 class="text-base font-semibold text-gray-100">
      Torrents for <span class="text-teal-400">"{title}"</span>
    </h1>
  </div>

  <!-- Media type toggle (applies to all Add actions on this page) -->
  <div class="flex gap-2 max-w-xs">
    {#each [['movie', 'Movie'], ['tv', 'TV Show']] as [val, label]}
      <label class="flex items-center gap-2 cursor-pointer flex-1 bg-gray-900 border rounded-lg px-3 py-2 transition text-sm font-medium {selectedType === val ? 'border-teal-500 text-teal-300' : 'border-gray-700 text-gray-400 hover:border-gray-600'}">
        <input type="radio" bind:group={selectedType} value={val} class="accent-teal-500" />
        {label}
      </label>
    {/each}
  </div>

  <!-- Loading -->
  {#if loading}
    <div class="flex flex-col gap-2">
      {#each Array(6) as _}
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-4 animate-pulse flex gap-4">
          <div class="flex-1 flex flex-col gap-2">
            <div class="h-3.5 bg-gray-700 rounded w-3/4"></div>
            <div class="h-2.5 bg-gray-800 rounded w-1/3"></div>
          </div>
          <div class="h-8 w-20 bg-gray-800 rounded-lg"></div>
        </div>
      {/each}
    </div>

  {:else if error}
    <div class="bg-red-900/20 border border-red-800 rounded-xl p-5 text-red-400 text-sm">
      Failed to fetch results: {error}
    </div>

  {:else if results.length === 0}
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-10 text-center text-gray-600 text-sm">
      No results found for "{title}".
    </div>

  {:else}
    <div class="flex flex-col gap-2">
      {#each results as r (r.id)}
        <div class="bg-gray-900 border rounded-xl overflow-hidden transition {confirming === r.id ? 'border-teal-700' : 'border-gray-800'}">
          <!-- Main row -->
          <div class="p-4 flex items-start gap-4">
            <!-- Left: title + meta -->
            <div class="flex-1 min-w-0 flex flex-col gap-1.5">
              <p class="text-sm text-gray-100 font-medium leading-snug" title={r.title}>{r.title}</p>
              <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500">
                <span class="bg-gray-800 px-1.5 py-0.5 rounded text-gray-400">{r.category}</span>
                <span>{r.size}</span>
                <span class="font-medium {seederColor(r.seeders)}">▲ {fmtSeeders(r.seeders)}</span>
                <span class="text-gray-600">▼ {r.leechers}</span>
                <span>{r.date}</span>
                {#if r.uploader}
                  <span class="text-gray-600">by {r.uploader}</span>
                {/if}
              </div>
            </div>

            <!-- Right: action button -->
            {#if addDone[r.id]}
              <span class="shrink-0 text-xs font-semibold text-emerald-400 px-3 py-2">✓ Added</span>
            {:else}
              <button
                onclick={() => confirming === r.id ? confirming = null : openConfirm(r)}
                class="shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition {confirming === r.id ? 'bg-gray-700 text-gray-300' : 'bg-teal-700 hover:bg-teal-600 text-white'}"
              >
                {#if confirming === r.id}
                  ✕ Cancel
                {:else}
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Add
                {/if}
              </button>
            {/if}
          </div>

          <!-- Inline confirm panel -->
          {#if confirming === r.id}
            <div class="border-t border-gray-800 bg-gray-950/50 px-4 py-3 flex flex-col gap-3">
              {#if selectedType === 'tv'}
                <div class="flex items-center gap-3">
                  <label class="text-xs text-gray-500 font-medium shrink-0 w-24">Show folder</label>
                  <input
                    type="text"
                    bind:value={tvShowFolder}
                    list="tv-folders"
                    class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-200 font-mono focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                  <datalist id="tv-folders">
                    {#each existingTvFolders as f}
                      <option value={f}></option>
                    {/each}
                  </datalist>
                </div>
                <div class="flex items-center gap-3">
                  <label class="text-xs text-gray-500 font-medium shrink-0 w-24">Episode folder</label>
                  <input
                    type="text"
                    bind:value={folderNames[r.id]}
                    class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-200 font-mono focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>
              {:else}
                <div class="flex items-center gap-3">
                  <label class="text-xs text-gray-500 font-medium shrink-0">Folder name</label>
                  <input
                    type="text"
                    bind:value={folderNames[r.id]}
                    class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-200 font-mono focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>
              {/if}
              <p class="text-xs font-mono text-gray-600 truncate">→ {computePath(r.id)}</p>
              {#if addError[r.id]}
                <p class="text-red-400 text-xs">{addError[r.id]}</p>
              {/if}
              <button
                onclick={() => handleAdd(r)}
                disabled={adding[r.id]}
                class="self-start px-4 py-1.5 bg-teal-600 hover:bg-teal-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-xs font-medium text-white transition"
              >
                {adding[r.id] ? 'Adding…' : `Send to qBittorrent → ${BASE_PATHS[selectedType]}/`}
              </button>
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>
