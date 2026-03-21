<script>
  import { onMount } from 'svelte'
  import { fetchTrending, fetchSearch, fetchDiscover, fetchItemsByFlag } from './lib/api.js'
  import { loadStates, getState } from './lib/itemStates.svelte.js'
  import MovieCard from './lib/MovieCard.svelte'
  import FilterBar from './lib/FilterBar.svelte'
  import SearchBar from './lib/SearchBar.svelte'
  import Downloads from './lib/Downloads.svelte'
  import TorrentSearch from './lib/TorrentSearch.svelte'
  import EpisodePicker from './lib/EpisodePicker.svelte'
  import BatchDownload from './lib/BatchDownload.svelte'

  // ---------- Routing ----------
  function parseHash() {
    const raw = (window.location.hash || '#/').slice(1)
    const qIdx = raw.indexOf('?')
    const path = (qIdx >= 0 ? raw.slice(0, qIdx) : raw) || '/'
    const params = new URLSearchParams(qIdx >= 0 ? raw.slice(qIdx + 1) : '')
    return { path, params }
  }

  function navigate(path, params = {}) {
    const entries = Object.entries(params).filter(([, v]) => v != null && v !== '')
    const qs = new URLSearchParams(entries).toString()
    window.location.hash = qs ? `${path}?${qs}` : path
  }

  function browseTo(overrides = {}) {
    const tab    = overrides.tab    ?? activeTab
    const q      = 'q'      in overrides ? overrides.q      : searchQuery
    const status = overrides.status ?? statusFilter
    const sort   = overrides.sort   ?? sortBy
    const genre  = 'genre'  in overrides ? overrides.genre  : genreFilter
    const p = {}
    if (tab    !== 'trending') p.tab    = tab
    if (q)                     p.q      = q
    if (status !== 'all')      p.status = status
    if (sort   !== 'default')  p.sort   = sort
    if (genre  !== null)       p.genre  = genre
    navigate('/', p)
  }

  // ---------- View state ----------
  let activeView          = $state('browse')
  let torrentTitle        = $state('')
  let torrentMediaType    = $state('movie')
  let torrentTmdbId       = $state(null)
  let torrentPosterUrl    = $state(null)
  let torrentSeasonNumber = $state(null)
  let torrentEpisodeNumber = $state(null)
  let torrentEpisodeName  = $state(null)
  let batchEpisodes       = $state([])

  // ---------- Browse state ----------
  const GENRES = {
    28:'Action', 12:'Adventure', 16:'Animation', 35:'Comedy', 80:'Crime',
    99:'Documentary', 18:'Drama', 10751:'Family', 14:'Fantasy', 36:'History',
    27:'Horror', 10402:'Music', 9648:'Mystery', 10749:'Romance', 878:'Sci-Fi',
    53:'Thriller', 10752:'War', 37:'Western', 10759:'Action & Adventure',
    10762:'Kids', 10763:'News', 10764:'Reality', 10765:'Sci-Fi & Fantasy',
    10766:'Soap', 10767:'Talk', 10768:'War & Politics',
  }
  const TRACKED_FILTERS = ['downloaded', 'watched', 'skipped']

  let activeTab     = $state('trending')
  let statusFilter  = $state('all')
  let genreFilter   = $state(null)
  let sortBy        = $state('default')
  let searchQuery   = $state('')
  let results       = $state([])
  let trackedResults = $state([])
  let loading       = $state(false)
  let error         = $state(null)
  let page          = $state(1)
  let totalPages    = $state(1)

  let activeResults = $derived(TRACKED_FILTERS.includes(statusFilter) ? trackedResults : results)

  let visibleResults = $derived.by(() => {
    let items = activeResults.filter(item => {
      if (TRACKED_FILTERS.includes(statusFilter)) {
        if (activeTab === 'movies' && item.media_type !== 'movie') return false
        if (activeTab === 'tv'     && item.media_type !== 'tv')    return false
      }
      const s = getState(item.id, item.media_type)
      if (statusFilter === 'skipped') return s.not_interested
      if (s.not_interested) return false
      if (statusFilter === 'watched')    return s.watched
      if (statusFilter === 'downloaded') return s.downloaded
      if (genreFilter !== null && !(item.genre_ids || []).includes(genreFilter)) return false
      return true
    })
    if (sortBy === 'rating')  items = [...items].sort((a, b) => (b.vote_average ?? 0) - (a.vote_average ?? 0))
    if (sortBy === 'newest')  items = [...items].sort((a, b) => (b.release_date ?? '').localeCompare(a.release_date ?? ''))
    return items
  })

  let availableGenres = $derived.by(() => {
    if (TRACKED_FILTERS.includes(statusFilter)) return []
    const seen = new Map()
    for (const item of results) {
      for (const id of (item.genre_ids || [])) {
        if (GENRES[id] && !seen.has(id)) seen.set(id, GENRES[id])
      }
    }
    return [...seen.entries()].sort((a, b) => a[1].localeCompare(b[1]))
  })

  // ---------- Data loading ----------
  async function load(tab, query, pg = 1, genre = genreFilter) {
    loading = true
    error = null
    try {
      let data
      if (query.trim()) {
        data = await fetchSearch(query, pg)
      } else if (genre !== null) {
        const type = tab === 'trending' ? 'all' : (tab === 'tv' ? 'tv' : 'movie')
        data = await fetchDiscover(type, genre, pg)
      } else if (tab === 'trending') {
        data = await fetchTrending(pg)
      } else {
        data = await fetchTrending(pg, tab === 'tv' ? 'tv' : 'movie')
      }
      const newResults = pg === 1 ? data.results : [...results, ...data.results]
      results = newResults
      totalPages = data.total_pages
      page = data.page
      await loadStates(data.results.map(r => ({ tmdb_id: r.id, media_type: r.media_type })))
    } catch (e) {
      error = e.message
    } finally {
      loading = false
    }
  }

  async function loadTracked(status) {
    const flagMap = { downloaded: 'downloaded', watched: 'watched', skipped: 'not_interested' }
    loading = true
    error = null
    try {
      const items = await fetchItemsByFlag(flagMap[status])
      trackedResults = items
      await loadStates(items.map(r => ({ tmdb_id: r.id, media_type: r.media_type })))
    } catch (e) {
      error = e.message
    } finally {
      loading = false
    }
  }

  function loadMore() {
    load(activeTab, searchQuery, page + 1)
  }

  // ---------- Route application ----------
  function applyRoute() {
    const { path, params } = parseHash()

    if (path === '/downloads') {
      activeView = 'downloads'
      return
    }

    const tvEp = path.match(/^\/tv\/(\d+)\/episodes$/)
    if (tvEp) {
      activeView      = 'episode-picker'
      torrentTmdbId   = Number(tvEp[1])
      torrentTitle    = params.get('title') || ''
      torrentPosterUrl = params.get('poster') || null
      torrentMediaType = 'tv'
      return
    }

    const tvBatch = path.match(/^\/tv\/(\d+)\/batch$/)
    if (tvBatch) {
      activeView      = 'batch-download'
      torrentTmdbId   = Number(tvBatch[1])
      torrentTitle    = params.get('title') || ''
      torrentPosterUrl = params.get('poster') || null
      torrentMediaType = 'tv'
      try { batchEpisodes = JSON.parse(sessionStorage.getItem('batchEpisodes') || '[]') } catch { batchEpisodes = [] }
      return
    }

    const torrentRoute = path.match(/^\/torrent\/(\d+)$/)
    if (torrentRoute) {
      activeView           = 'torrent-search'
      torrentTmdbId        = Number(torrentRoute[1])
      torrentTitle         = params.get('title') || ''
      torrentPosterUrl     = params.get('poster') || null
      torrentMediaType     = params.get('type') || 'movie'
      torrentSeasonNumber  = params.get('season') ? Number(params.get('season')) : null
      torrentEpisodeNumber = params.get('ep')     ? Number(params.get('ep'))     : null
      torrentEpisodeName   = params.get('epName') || null
      return
    }

    // Default: browse
    const newTab    = params.get('tab')    || 'trending'
    const newQuery  = params.get('q')      || ''
    const newStatus = params.get('status') || 'all'
    const newSort   = params.get('sort')   || 'default'
    const newGenre  = params.get('genre')  ? Number(params.get('genre')) : null

    const browseChanged = newTab !== activeTab || newQuery !== searchQuery ||
                          newStatus !== statusFilter || newGenre !== genreFilter

    activeView   = 'browse'
    activeTab    = newTab
    searchQuery  = newQuery
    statusFilter = newStatus
    sortBy       = newSort
    genreFilter  = newGenre

    if (browseChanged || results.length === 0) {
      if (TRACKED_FILTERS.includes(newStatus)) {
        loadTracked(newStatus)
      } else {
        load(newTab, newQuery, 1, newGenre)
      }
    }
  }

  onMount(() => {
    applyRoute()
    window.addEventListener('hashchange', applyRoute)
    return () => window.removeEventListener('hashchange', applyRoute)
  })

  // ---------- Navigation ----------
  function openTorrentSearch(title, mediaType, tmdbId, posterUrl) {
    if (mediaType === 'tv') {
      navigate(`/tv/${tmdbId}/episodes`, { title, poster: posterUrl })
    } else {
      navigate(`/torrent/${tmdbId}`, { type: 'movie', title, poster: posterUrl })
    }
  }
</script>

<div class="min-h-screen bg-gray-950 text-gray-100">
  <!-- Header -->
  <header class="sticky top-0 z-10 bg-gray-950/90 backdrop-blur border-b border-gray-800 px-4 py-3">
    <div class="max-w-7xl mx-auto flex items-center gap-3">
      <div class="flex items-center gap-2 shrink-0">
        <span class="text-teal-400 text-xl">🎬</span>
        <span class="font-bold text-lg tracking-tight text-white hidden sm:block">StreamScope</span>
      </div>
      <div class="flex-1 min-w-0">
        <SearchBar bind:value={searchQuery} onSearch={(q) => browseTo({ q, genre: null })} />
      </div>
      <button
        onclick={() => activeView === 'downloads' ? history.back() : navigate('/downloads')}
        class="shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition {activeView === 'downloads' ? 'bg-teal-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'}"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        <span class="hidden sm:block">Downloads</span>
      </button>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-4 py-6">
    {#if activeView === 'downloads'}
      <Downloads />
    {:else if activeView === 'episode-picker'}
      <EpisodePicker
        title={torrentTitle}
        tmdbId={torrentTmdbId}
        posterUrl={torrentPosterUrl}
        onSearch={(query, code, meta) => {
          navigate(`/torrent/${torrentTmdbId}`, {
            type: 'tv',
            title: query,
            poster: torrentPosterUrl,
            season: meta?.seasonNumber,
            ep: meta?.episodeNumber,
            epName: meta?.episodeName,
          })
        }}
        onBatchDownload={(episodes) => {
          sessionStorage.setItem('batchEpisodes', JSON.stringify(episodes))
          navigate(`/tv/${torrentTmdbId}/batch`, { title: torrentTitle, poster: torrentPosterUrl })
        }}
        onBack={() => history.back()}
      />
    {:else if activeView === 'batch-download'}
      <BatchDownload
        showTitle={torrentTitle}
        tmdbId={torrentTmdbId}
        posterUrl={torrentPosterUrl}
        episodes={batchEpisodes}
        onBack={() => history.back()}
      />
    {:else if activeView === 'torrent-search'}
      <TorrentSearch
        title={torrentTitle}
        mediaType={torrentMediaType}
        tmdbId={torrentTmdbId}
        posterUrl={torrentPosterUrl}
        seasonNumber={torrentSeasonNumber}
        episodeNumber={torrentEpisodeNumber}
        episodeName={torrentEpisodeName}
        onBack={() => history.back()}
      />
    {:else}
    <!-- Filter tabs -->
    <div class="mb-6 flex flex-col sm:flex-row sm:items-center gap-3">
      {#if !searchQuery}
        <div class="max-w-sm w-full">
          <FilterBar {activeTab} onchange={(tab) => browseTo({ tab, q: '', genre: null })} />
        </div>
      {:else}
        <p class="text-gray-400 text-sm">
          Results for <span class="text-white font-medium">"{searchQuery}"</span>
        </p>
      {/if}

      <!-- Mobile: dropdowns -->
      <div class="flex gap-2 sm:hidden">
        <select
          value={sortBy}
          onchange={(e) => browseTo({ sort: e.target.value })}
          class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-teal-500"
        >
          <option value="default">Sort: Default</option>
          <option value="rating">Sort: Rating</option>
          <option value="newest">Sort: Newest</option>
        </select>
        <select
          value={statusFilter}
          onchange={(e) => browseTo({ status: e.target.value })}
          class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-teal-500"
        >
          <option value="all">All</option>
          <option value="watched">Watched</option>
          <option value="downloaded">Downloaded</option>
          <option value="skipped">Skipped</option>
        </select>
      </div>

      <!-- Desktop: pills -->
      <div class="hidden sm:flex sm:ml-auto gap-1.5">
        <div class="flex gap-1">
          {#each [['default','Default'],['rating','Rating'],['newest','Newest']] as [val, label]}
            <button
              onclick={() => browseTo({ sort: val })}
              class="px-2.5 py-1.5 rounded-full text-xs font-medium transition whitespace-nowrap
                {sortBy === val ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'}"
            >{label}</button>
          {/each}
        </div>
        <div class="w-px bg-gray-700 self-stretch"></div>
        <div class="flex gap-1">
          {#each [['all','All'],['watched','Watched'],['downloaded','Downloaded'],['skipped','Skipped']] as [val, label]}
            <button
              onclick={() => browseTo({ status: val })}
              class="px-2.5 py-1.5 rounded-full text-xs font-medium transition whitespace-nowrap
                {statusFilter === val ? 'bg-teal-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'}"
            >{label}</button>
          {/each}
        </div>
      </div>
    </div>

    <!-- Genre filter -->
    {#if availableGenres.length > 0}
      <!-- Mobile: dropdown -->
      <select
        value={genreFilter === null ? '' : String(genreFilter)}
        onchange={(e) => browseTo({ genre: e.target.value ? Number(e.target.value) : null })}
        class="sm:hidden w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-teal-500 mb-4 -mt-1"
      >
        <option value="">All genres</option>
        {#each availableGenres as [id, name]}
          <option value={String(id)}>{name}</option>
        {/each}
      </select>

      <!-- Desktop: pills -->
      <div class="hidden sm:flex gap-1.5 mb-4 -mt-2">
        {#if genreFilter !== null}
          <button
            onclick={() => browseTo({ genre: null })}
            class="shrink-0 px-2.5 py-1.5 rounded-full text-xs font-medium transition whitespace-nowrap bg-gray-800 text-gray-500 hover:bg-gray-700 hover:text-gray-300"
          >All genres</button>
        {/if}
        {#each availableGenres as [id, name]}
          <button
            onclick={() => browseTo({ genre: genreFilter === id ? null : id })}
            class="shrink-0 px-2.5 py-1.5 rounded-full text-xs font-medium transition whitespace-nowrap
              {genreFilter === id ? 'bg-gray-600 text-white' : 'bg-gray-800 text-gray-500 hover:bg-gray-700 hover:text-gray-300'}"
          >{name}</button>
        {/each}
      </div>
    {/if}

    <!-- Error state -->
    {#if error}
      <div class="flex flex-col items-center justify-center py-20 gap-3 text-center">
        <p class="text-red-400 text-lg font-medium">Failed to load content</p>
        <p class="text-gray-500 text-sm">{error}</p>
        <button
          class="mt-2 px-4 py-2 bg-teal-700 hover:bg-teal-600 rounded-lg text-sm font-medium transition"
          onclick={() => applyRoute()}
        >
          Try again
        </button>
      </div>
    {:else}
      <!-- Grid -->
      <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
        {#each visibleResults as item (item.id + item.media_type)}
          <MovieCard {item} onFindTorrents={openTorrentSearch} />
        {/each}

        <!-- Skeleton loaders -->
        {#if loading}
          {#each Array(12) as _}
            <div class="flex flex-col bg-gray-900 rounded-xl overflow-hidden border border-gray-800 animate-pulse">
              <div class="aspect-[2/3] bg-gray-800"></div>
              <div class="p-3 flex flex-col gap-2">
                <div class="h-3 bg-gray-700 rounded w-3/4"></div>
                <div class="h-2.5 bg-gray-800 rounded w-1/3"></div>
              </div>
            </div>
          {/each}
        {/if}
      </div>

      <!-- Empty state -->
      {#if !loading && visibleResults.length === 0}
        <div class="flex flex-col items-center justify-center py-20 gap-2 text-center">
          <p class="text-gray-500 text-lg">No results found</p>
          {#if searchQuery}
            <p class="text-gray-600 text-sm">Try a different search term</p>
          {/if}
        </div>
      {/if}

      <!-- Load more -->
      {#if !loading && !TRACKED_FILTERS.includes(statusFilter) && results.length > 0 && page < totalPages}
        <div class="flex justify-center mt-8">
          <button
            class="px-6 py-2.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-xl text-sm font-medium text-gray-200 transition"
            onclick={loadMore}
          >
            Load more
          </button>
        </div>
      {/if}
    {/if}
    {/if}
  </main>
</div>
