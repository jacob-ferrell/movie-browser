<script>
  import { onMount } from 'svelte'
  import { fetchDetail, fetchProviders } from './api.js'
  import { getState, setFlag } from './itemStates.svelte.js'

  let { item, onBack, onFindTorrents } = $props()

  let detail = $state(null)
  let providers = $state(null)
  let loading = $state(true)
  let error = $state(null)
  let flagging = $state(null)

  let state = $derived(getState(item.id, item.media_type))

  const year = (date) => date ? date.slice(0, 4) : '—'

  const ratingColor = (r) => {
    if (r >= 7.5) return 'text-emerald-400'
    if (r >= 6.0) return 'text-amber-400'
    return 'text-red-400'
  }

  async function toggle(flag) {
    flagging = flag
    const d = detail || item
    try {
      await setFlag(d.id, d.media_type, d.title, d.poster_url, flag, !state[flag])
    } finally {
      flagging = null
    }
  }

  onMount(async () => {
    try {
      const [d, p] = await Promise.all([
        fetchDetail(item.media_type, item.id),
        fetchProviders(item.media_type, item.id),
      ])
      detail = d
      providers = p
    } catch (e) {
      error = e.message
    } finally {
      loading = false
    }
  })
</script>

<div class="min-h-screen">
  <!-- Back button -->
  <button
    onclick={onBack}
    class="flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition mb-4"
  >
    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
    </svg>
    Back
  </button>

  {#if loading}
    <!-- Skeleton -->
    <div class="animate-pulse">
      <div class="w-full h-64 bg-gray-800 rounded-xl mb-6"></div>
      <div class="flex gap-6">
        <div class="w-32 h-48 bg-gray-800 rounded-lg shrink-0"></div>
        <div class="flex-1 flex flex-col gap-3 pt-2">
          <div class="h-6 bg-gray-700 rounded w-2/3"></div>
          <div class="h-4 bg-gray-800 rounded w-1/4"></div>
          <div class="h-4 bg-gray-800 rounded w-full mt-2"></div>
          <div class="h-4 bg-gray-800 rounded w-5/6"></div>
          <div class="h-4 bg-gray-800 rounded w-4/6"></div>
        </div>
      </div>
    </div>

  {:else if error}
    <div class="flex flex-col items-center justify-center py-20 gap-3 text-center">
      <p class="text-red-400 text-lg font-medium">Failed to load details</p>
      <p class="text-gray-500 text-sm">{error}</p>
    </div>

  {:else}
    {@const d = detail}

    <!-- Backdrop hero -->
    {#if d.backdrop_url}
      <div class="relative w-full h-56 sm:h-72 rounded-xl overflow-hidden mb-6">
        <img src={d.backdrop_url} alt="" class="w-full h-full object-cover" />
        <div class="absolute inset-0 bg-gradient-to-t from-gray-950 via-gray-950/40 to-transparent"></div>
      </div>
    {/if}

    <!-- Poster + info -->
    <div class="flex gap-5 sm:gap-8 mb-8">
      {#if d.poster_url}
        <img
          src={d.poster_url}
          alt={d.title}
          class="w-28 sm:w-40 rounded-lg shrink-0 shadow-xl shadow-black/60 {d.backdrop_url ? '-mt-20 sm:-mt-28 relative z-10' : ''}"
        />
      {/if}

      <div class="flex-1 min-w-0 flex flex-col gap-2 pt-1">
        <!-- Type badge -->
        <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full w-fit
          {d.media_type === 'tv' ? 'bg-purple-600/90 text-purple-100' : 'bg-blue-600/90 text-blue-100'}">
          {d.media_type === 'tv' ? 'TV Series' : 'Film'}
        </span>

        <h1 class="text-xl sm:text-3xl font-bold text-white leading-tight">{d.title}</h1>

        {#if d.tagline}
          <p class="text-sm text-gray-500 italic">{d.tagline}</p>
        {/if}

        <!-- Meta row -->
        <div class="flex flex-wrap items-center gap-3 text-sm text-gray-400">
          <span>{year(d.release_date)}</span>
          {#if d.vote_average > 0}
            <span class="font-semibold {ratingColor(d.vote_average)}">★ {d.vote_average}</span>
          {/if}
          {#if d.runtime}
            <span>{Math.floor(d.runtime / 60)}h {d.runtime % 60}m</span>
          {/if}
          {#if d.number_of_seasons}
            <span>{d.number_of_seasons} season{d.number_of_seasons !== 1 ? 's' : ''}</span>
          {/if}
          {#if d.status}
            <span class="text-gray-600">{d.status}</span>
          {/if}
        </div>

        <!-- Genres -->
        {#if d.genres?.length}
          <div class="flex flex-wrap gap-1.5 mt-1">
            {#each d.genres as genre}
              <span class="text-xs px-2.5 py-1 rounded-full bg-gray-800 text-gray-300">{genre}</span>
            {/each}
          </div>
        {/if}

        <!-- Action buttons (desktop) -->
        <div class="hidden sm:flex gap-2 mt-3">
          <button
            onclick={() => toggle('watched')}
            disabled={flagging === 'watched'}
            class="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-50
              {state.watched ? 'bg-emerald-700/60 text-emerald-300 hover:bg-emerald-700' : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'}"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
            {state.watched ? 'Watched' : 'Mark Watched'}
          </button>
          <button
            onclick={() => toggle('not_interested')}
            disabled={flagging === 'not_interested'}
            class="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-50
              {state.not_interested ? 'bg-red-900/50 text-red-400 hover:bg-red-900' : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'}"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
            {state.not_interested ? 'Undo Skip' : 'Skip'}
          </button>
          {#if onFindTorrents}
            <button
              onclick={() => onFindTorrents(d.title, d.media_type, d.id, d.poster_url)}
              class="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-teal-700 hover:bg-teal-600 text-white text-sm font-medium transition"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Find Torrents
            </button>
          {/if}
        </div>
      </div>
    </div>

    <!-- Action buttons (mobile) -->
    <div class="flex sm:hidden gap-2 mb-6">
      <button
        onclick={() => toggle('watched')}
        disabled={flagging === 'watched'}
        class="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-sm font-medium transition disabled:opacity-50
          {state.watched ? 'bg-emerald-700/60 text-emerald-300' : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'}"
      >
        {state.watched ? 'Watched' : 'Watch'}
      </button>
      <button
        onclick={() => toggle('not_interested')}
        disabled={flagging === 'not_interested'}
        class="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-sm font-medium transition disabled:opacity-50
          {state.not_interested ? 'bg-red-900/50 text-red-400' : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'}"
      >
        {state.not_interested ? 'Undo Skip' : 'Skip'}
      </button>
      {#if onFindTorrents}
        <button
          onclick={() => onFindTorrents(d.title, d.media_type, d.id, d.poster_url)}
          class="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-lg bg-teal-700 text-white text-sm font-medium transition"
        >
          Torrents
        </button>
      {/if}
    </div>

    <!-- Overview -->
    {#if d.overview}
      <div class="mb-8">
        <h2 class="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-2">Overview</h2>
        <p class="text-gray-300 leading-relaxed">{d.overview}</p>
      </div>
    {/if}

    <!-- Streaming providers -->
    {#if providers}
      {#if providers.stream.length > 0 || providers.rent.length > 0 || providers.buy.length > 0}
        <div class="mb-8">
          <h2 class="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-3">Where to Watch</h2>
          <div class="flex flex-col gap-3">
            {#if providers.stream.length > 0}
              <div>
                <p class="text-[10px] uppercase tracking-wider text-teal-500 font-semibold mb-1.5">Stream</p>
                <div class="flex flex-wrap gap-2">
                  {#each providers.stream as p}
                    <img src={p.logo_url} alt={p.name} title={p.name} class="w-10 h-10 rounded-lg object-cover" loading="lazy" />
                  {/each}
                </div>
              </div>
            {/if}
            {#if providers.rent.length > 0}
              <div>
                <p class="text-[10px] uppercase tracking-wider text-amber-500 font-semibold mb-1.5">Rent</p>
                <div class="flex flex-wrap gap-2">
                  {#each providers.rent as p}
                    <img src={p.logo_url} alt={p.name} title={p.name} class="w-10 h-10 rounded-lg object-cover" loading="lazy" />
                  {/each}
                </div>
              </div>
            {/if}
            {#if providers.buy.length > 0}
              <div>
                <p class="text-[10px] uppercase tracking-wider text-blue-400 font-semibold mb-1.5">Buy</p>
                <div class="flex flex-wrap gap-2">
                  {#each providers.buy as p}
                    <img src={p.logo_url} alt={p.name} title={p.name} class="w-10 h-10 rounded-lg object-cover" loading="lazy" />
                  {/each}
                </div>
              </div>
            {/if}
            {#if providers.link}
              <a
                href={providers.link}
                target="_blank"
                rel="noopener noreferrer"
                class="text-xs text-teal-500 hover:text-teal-400 underline w-fit"
              >View on JustWatch →</a>
            {/if}
          </div>
        </div>
      {/if}
    {/if}
  {/if}
</div>
