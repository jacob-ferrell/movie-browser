<script>
  import { fetchTvSeasons, fetchTvEpisodes } from './api.js'

  let { title, tmdbId, posterUrl, onSearch, onBack, onBatchDownload = null } = $props()

  let seasons = $state([])
  let episodes = $state([])
  let selectedSeason = $state(null)
  let loadingSeasons = $state(true)
  let loadingEpisodes = $state(false)
  let error = $state(null)
  let selectedEpisodes = $state(new Set())

  function toggleEpisode(epNum) {
    const next = new Set(selectedEpisodes)
    if (next.has(epNum)) next.delete(epNum)
    else next.add(epNum)
    selectedEpisodes = next
  }

  function toggleAll() {
    if (selectedEpisodes.size === episodes.length) selectedEpisodes = new Set()
    else selectedEpisodes = new Set(episodes.map(e => e.episode_number))
  }

  function handleBatchDownload() {
    const selected = episodes.filter(e => selectedEpisodes.has(e.episode_number))
    onBatchDownload(selected.map(ep => ({
      query: `${title} ${episodeCode(selectedSeason.season_number, ep.episode_number)}`,
      code: episodeCode(selectedSeason.season_number, ep.episode_number),
      seasonNumber: selectedSeason.season_number,
      episodeNumber: ep.episode_number,
      episodeName: ep.name,
    })))
  }

  function pad(n) {
    return String(n).padStart(2, '0')
  }

  function episodeCode(season, episode) {
    return `S${pad(season)}E${pad(episode)}`
  }

  function handleSearch(episode) {
    const code = episodeCode(selectedSeason.season_number, episode.episode_number)
    onSearch(`${title} ${code}`, code, {
      seasonNumber: selectedSeason.season_number,
      episodeNumber: episode.episode_number,
      episodeName: episode.name,
    })
  }

  async function selectSeason(season) {
    selectedSeason = season
    loadingEpisodes = true
    episodes = []
    try {
      episodes = await fetchTvEpisodes(tmdbId, season.season_number)
    } catch (e) {
      error = e.message
    } finally {
      loadingEpisodes = false
    }
  }

  $effect(() => {
    fetchTvSeasons(tmdbId)
      .then(data => { seasons = data; loadingSeasons = false })
      .catch(e => { error = e.message; loadingSeasons = false })
  })
</script>

<div class="max-w-4xl mx-auto py-6 flex flex-col gap-5">
  <!-- Header -->
  <div class="flex items-center gap-3">
    <button
      onclick={selectedSeason ? () => { selectedSeason = null; episodes = [] } : onBack}
      class="flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-100 transition"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      {selectedSeason ? 'Seasons' : 'Back'}
    </button>
    <div class="h-4 w-px bg-gray-700"></div>
    <div class="flex items-center gap-2 min-w-0">
      {#if posterUrl}
        <img src={posterUrl} alt={title} class="w-6 h-9 rounded object-cover shrink-0" />
      {/if}
      <h1 class="text-base font-semibold text-gray-100 truncate">
        {title}
        {#if selectedSeason}
          <span class="text-gray-400 font-normal"> — {selectedSeason.name}</span>
        {/if}
      </h1>
    </div>
  </div>

  {#if error}
    <div class="bg-red-900/20 border border-red-800 rounded-xl p-4 text-red-400 text-sm">{error}</div>

  {:else if loadingSeasons}
    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
      {#each Array(8) as _}
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-4 animate-pulse h-20"></div>
      {/each}
    </div>

  {:else if !selectedSeason}
    <!-- Season grid -->
    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
      {#each seasons as season}
        <button
          onclick={() => selectSeason(season)}
          class="bg-gray-900 border border-gray-800 hover:border-teal-600 rounded-xl p-4 text-left flex flex-col gap-1 transition hover:bg-gray-800"
        >
          <span class="text-sm font-semibold text-gray-100">{season.name}</span>
          <span class="text-xs text-gray-500">{season.episode_count} episode{season.episode_count !== 1 ? 's' : ''}</span>
          {#if season.air_date}
            <span class="text-xs text-gray-600">{season.air_date.slice(0, 4)}</span>
          {/if}
        </button>
      {/each}
    </div>

  {:else}
    <!-- Episode list -->
    {#if loadingEpisodes}
      <div class="flex flex-col gap-2">
        {#each Array(10) as _}
          <div class="bg-gray-900 border border-gray-800 rounded-xl p-4 animate-pulse h-16"></div>
        {/each}
      </div>
    {:else}
      <!-- Select all + batch download controls -->
      {#if onBatchDownload}
        <div class="flex items-center gap-3 pl-9">
          <button onclick={toggleAll} class="text-sm text-gray-400 hover:text-gray-200 transition select-none">
            {selectedEpisodes.size === episodes.length && episodes.length > 0 ? 'Deselect all' : 'Select all'}
          </button>
          {#if selectedEpisodes.size > 0}
            <button
              onclick={handleBatchDownload}
              class="ml-auto flex items-center gap-1.5 px-3 py-1.5 bg-teal-600 hover:bg-teal-500 text-white text-xs font-medium rounded-lg transition"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download {selectedEpisodes.size} episode{selectedEpisodes.size !== 1 ? 's' : ''}
            </button>
          {/if}
        </div>
      {/if}

      <div class="flex flex-col gap-2">
        {#each episodes as ep}
          <div class="flex items-center gap-2">
            <!-- Circular toggle outside the card -->
            {#if onBatchDownload}
              <button
                onclick={() => toggleEpisode(ep.episode_number)}
                class="shrink-0 w-7 h-7 rounded-full flex items-center justify-center transition
                  {selectedEpisodes.has(ep.episode_number)
                    ? 'bg-teal-500 text-white'
                    : 'bg-gray-800 border border-gray-600 text-transparent hover:border-gray-400'}"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                </svg>
              </button>
            {/if}

            <!-- Card -->
            <div class="flex-1 bg-gray-900 border border-gray-800 hover:border-gray-700 rounded-xl p-4 flex items-center gap-4 transition">
              <!-- Still image -->
              {#if ep.still_url}
                <img src={ep.still_url} alt={ep.name} class="w-20 h-12 rounded-lg object-cover shrink-0 bg-gray-800 hidden sm:block" loading="lazy" />
              {/if}

              <!-- Info -->
              <div
                class="flex-1 min-w-0 cursor-pointer"
                role="button"
                tabindex="0"
                onclick={() => onBatchDownload ? toggleEpisode(ep.episode_number) : handleSearch(ep)}
                onkeydown={(e) => e.key === 'Enter' && (onBatchDownload ? toggleEpisode(ep.episode_number) : handleSearch(ep))}
              >
                <div class="flex items-center gap-2">
                  <span class="text-xs font-bold text-teal-500 font-mono shrink-0">
                    {episodeCode(selectedSeason.season_number, ep.episode_number)}
                  </span>
                  <span class="text-sm font-medium text-gray-100 truncate">{ep.name}</span>
                </div>
                {#if ep.overview}
                  <p class="text-xs text-gray-500 mt-0.5 line-clamp-1 leading-relaxed">{ep.overview}</p>
                {/if}
                <div class="flex gap-3 mt-0.5 text-xs text-gray-600">
                  {#if ep.air_date}<span>{ep.air_date}</span>{/if}
                  {#if ep.runtime}<span>{ep.runtime}m</span>{/if}
                </div>
              </div>

              <!-- Single-episode search button -->
              <button
                onclick={() => handleSearch(ep)}
                class="shrink-0 text-xs text-gray-600 hover:text-teal-500 transition font-mono px-2 py-1"
              >
                Find →
              </button>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  {/if}
</div>
