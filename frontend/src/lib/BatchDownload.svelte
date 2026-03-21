<script>
  import { searchTorrents, addMagnet, recordDownload, fetchShowFolder } from './api.js'
  import { setFlag } from './itemStates.svelte.js'

  let { showTitle, tmdbId, posterUrl, episodes, onBack } = $props()
  // episodes: [{query, code, seasonNumber, episodeNumber, episodeName}]

  const BASE_TV = '/hdd/tvshows'

  let tvShowFolder = $state(normalizeShow(showTitle))
  let results    = $state({})  // episodeNumber → torrent result | null
  let searching  = $state({})  // episodeNumber → true/false
  let searchErr  = $state({})  // episodeNumber → error string
  let folderNames = $state({}) // episodeNumber → episode folder string
  let selected   = $state(new Set(episodes.map(e => e.episodeNumber)))
  let adding     = $state(false)
  let addStatus  = $state({})  // episodeNumber → 'done' | string (error)

  function normalizeShow(t) {
    return (t || '').replace(/\s*S\d{2}E\d{2}.*/i, '').trim()
      .replace(/[<>:"/\\|?*]/g, '').replace(/\s+/g, '.')
  }

  function extractEpisodeFolder(raw) {
    let s = raw.replace(/\[.*?\]/g, '').replace(/[\s.]+/g, '.')
    const epMatch = s.match(/S\d{2}E\d{2}/i)
    if (epMatch) {
      return s.slice(0, epMatch.index + epMatch[0].length)
        .replace(/\.{2,}/g, '.').replace(/^\.+|\.+$/g, '')
    }
    return s.replace(/[^a-zA-Z0-9.]/g, '.').replace(/\.{2,}/g, '.').replace(/^\.+|\.+$/g, '')
  }

  function computePath(episodeNumber) {
    const show = tvShowFolder.trim().replace(/\.{2,}/g, '.').replace(/^\.+|\.+$/g, '')
    const ep   = (folderNames[episodeNumber] || '').trim()
    if (show && ep) return `${BASE_TV}/${show}/${ep}`
    if (show) return `${BASE_TV}/${show}`
    return BASE_TV
  }

  function extractHash(magnet) {
    const m = (magnet || '').match(/xt=urn:btih:([a-fA-F0-9]+)/i)
    return m ? m[1].toLowerCase() : null
  }

  function toggleEpisode(num) {
    const next = new Set(selected)
    if (next.has(num)) next.delete(num)
    else next.add(num)
    selected = next
  }

  let allSelected = $derived(selected.size === episodes.length)
  let readyCount  = $derived(episodes.filter(e => selected.has(e.episodeNumber) && results[e.episodeNumber]).length)

  $effect(() => {
    if (tmdbId) {
      fetchShowFolder(tmdbId).then(d => { if (d.folder) tvShowFolder = d.folder }).catch(() => {})
    }
    for (const ep of episodes) {
      searching[ep.episodeNumber] = true
      searchTorrents(ep.query)
        .then(data => {
          results[ep.episodeNumber] = data[0] ?? null
          if (data[0]) folderNames[ep.episodeNumber] = extractEpisodeFolder(data[0].title)
          searching[ep.episodeNumber] = false
        })
        .catch(e => {
          searchErr[ep.episodeNumber] = e.message
          searching[ep.episodeNumber] = false
        })
    }
  })

  async function handleDownload() {
    adding = true
    const toDownload = episodes.filter(e => selected.has(e.episodeNumber) && results[e.episodeNumber])
    await Promise.all(toDownload.map(async ep => {
      const result   = results[ep.episodeNumber]
      const savePath = computePath(ep.episodeNumber)
      try {
        await addMagnet(result.magnet, savePath)
        if (tmdbId) {
          recordDownload({
            tmdb_id: tmdbId, media_type: 'tv', title: showTitle, poster_url: posterUrl,
            save_path: savePath, torrent_name: result.title, torrent_hash: extractHash(result.magnet),
            season_number: ep.seasonNumber, episode_number: ep.episodeNumber, episode_name: ep.episodeName,
          }).catch(() => {})
        }
        addStatus[ep.episodeNumber] = 'done'
      } catch (e) {
        addStatus[ep.episodeNumber] = e.message
      }
    }))
    if (tmdbId) setFlag(tmdbId, 'tv', showTitle, posterUrl, 'downloaded', true).catch(() => {})
    adding = false
  }

  let allDone = $derived(
    episodes.filter(e => selected.has(e.episodeNumber)).every(e => addStatus[e.episodeNumber] === 'done')
  )
</script>

<div class="max-w-4xl mx-auto py-6 flex flex-col gap-5">
  <!-- Header -->
  <div class="flex items-center gap-3">
    <button onclick={onBack} class="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-100 transition">
      <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      Back
    </button>
    <div class="h-4 w-px bg-gray-700"></div>
    <div class="flex items-center gap-2 min-w-0">
      {#if posterUrl}
        <img src={posterUrl} alt={showTitle} class="w-6 h-9 rounded object-cover shrink-0" />
      {/if}
      <h1 class="text-base font-semibold text-gray-100 truncate">{showTitle} — Batch Download</h1>
    </div>
  </div>

  <!-- Shared show folder -->
  <div class="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col gap-2">
    <label class="text-xs text-gray-500 font-medium">Show folder (shared for all episodes)</label>
    <input
      type="text"
      bind:value={tvShowFolder}
      class="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-gray-200 font-mono focus:outline-none focus:ring-2 focus:ring-teal-500"
    />
    <p class="text-xs font-mono text-gray-600">{BASE_TV}/{tvShowFolder || '<show>'}/</p>
  </div>

  <!-- Select all + episode count -->
  <div class="flex items-center gap-3 pl-9">
    <button
      onclick={() => selected = allSelected ? new Set() : new Set(episodes.map(e => e.episodeNumber))}
      class="text-sm text-gray-400 hover:text-gray-200 transition select-none"
    >
      {allSelected ? 'Deselect all' : 'Select all'}
    </button>
    <span class="text-xs text-gray-600 ml-auto">{episodes.length} episodes</span>
  </div>

  <!-- Episode list -->
  <div class="flex flex-col gap-2">
    {#each episodes as ep (ep.episodeNumber)}
      {@const r = results[ep.episodeNumber]}
      {@const done = addStatus[ep.episodeNumber] === 'done'}
      {@const err = addStatus[ep.episodeNumber] && addStatus[ep.episodeNumber] !== 'done'}
      <div class="flex items-start gap-2">
        <!-- Circular toggle outside the card -->
        <button
          onclick={() => toggleEpisode(ep.episodeNumber)}
          disabled={done}
          class="shrink-0 mt-3 w-7 h-7 rounded-full flex items-center justify-center transition disabled:opacity-40
            {selected.has(ep.episodeNumber)
              ? 'bg-teal-500 text-white'
              : 'bg-gray-800 border border-gray-600 text-transparent hover:border-gray-400'}"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
          </svg>
        </button>

        <div class="flex-1 bg-gray-900 border rounded-xl overflow-hidden transition
          {done ? 'border-emerald-800' : err ? 'border-red-900' : 'border-gray-800'}">

        <!-- Row -->
        <div class="p-3 flex items-center gap-3">
          <span class="text-xs font-bold font-mono text-teal-500 shrink-0 w-14">{ep.code}</span>
          <div class="flex-1 min-w-0">
            <p class="text-xs font-medium text-gray-200 truncate">{ep.episodeName}</p>
            {#if searching[ep.episodeNumber]}
              <p class="text-xs text-gray-600 mt-0.5">Searching…</p>
            {:else if searchErr[ep.episodeNumber]}
              <p class="text-xs text-red-400 mt-0.5 truncate">{searchErr[ep.episodeNumber]}</p>
            {:else if r}
              <p class="text-xs text-gray-500 mt-0.5 truncate" title={r.title}>{r.title}</p>
            {:else}
              <p class="text-xs text-amber-500 mt-0.5">No results found</p>
            {/if}
          </div>
          {#if done}
            <span class="shrink-0 text-xs font-semibold text-emerald-400">✓ Added</span>
          {:else if err}
            <span class="shrink-0 text-xs text-red-400" title={addStatus[ep.episodeNumber]}>Error</span>
          {:else if r}
            <span class="shrink-0 text-xs text-gray-600 font-mono">{r.size}</span>
          {/if}
        </div>

        <!-- Folder name (only when result found and not yet done) -->
        {#if r && !done && selected.has(ep.episodeNumber)}
          <div class="border-t border-gray-800 px-3 py-2 flex flex-col gap-1">
            <input
              type="text"
              bind:value={folderNames[ep.episodeNumber]}
              class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-300 font-mono focus:outline-none focus:ring-1 focus:ring-teal-500"
              placeholder="episode folder name"
            />
            <p class="text-xs font-mono text-gray-700 truncate">→ {computePath(ep.episodeNumber)}</p>
          </div>
        {/if}
        </div>
      </div>
    {/each}
  </div>

  <!-- Download button -->
  {#if !allDone}
    <div class="sticky bottom-4">
      <button
        onclick={handleDownload}
        disabled={adding || readyCount === 0}
        class="w-full py-3 bg-teal-600 hover:bg-teal-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl text-sm font-semibold text-white transition shadow-lg shadow-black/40"
      >
        {#if adding}
          Adding torrents…
        {:else}
          Download {readyCount} episode{readyCount !== 1 ? 's' : ''} →
        {/if}
      </button>
    </div>
  {:else}
    <div class="text-center py-3 text-emerald-400 text-sm font-semibold">All episodes added to qBittorrent ✓</div>
  {/if}
</div>
